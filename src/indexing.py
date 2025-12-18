import os
import re
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    SummaryIndex,
    Settings,
    Document,
)
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.schema import TextNode
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.query_engine import RetrieverQueryEngine


# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def parse_markdown_table(table_text: str, table_name: str) -> List[Dict[str, Any]]:
    """
    Parse a markdown table and return rows as dictionaries.
    
    Args:
        table_text: The markdown table text (including headers and separator)
        table_name: Name/identifier for the table
        
    Returns:
        List of dictionaries, each representing a row with headers as keys
    """
    # Split by lines and filter out empty lines
    all_lines = table_text.strip().split('\n')
    lines = []
    for line in all_lines:
        stripped = line.strip()
        if stripped:  # Only include non-empty lines
            lines.append(stripped)
    
    if len(lines) < 2:
        return []
    
    # Find the separator line (e.g., |---|---|)
    separator_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^\|[\s\-\|:]+\|$', line):
            separator_idx = i
            break
    
    if separator_idx is None or separator_idx == 0:
        return []
    
    # Extract headers (line before separator)
    header_line = lines[separator_idx - 1]
    if not header_line.startswith('|'):
        return []
    headers = [h.strip() for h in header_line.split('|')[1:-1]]
    
    if not headers:
        return []
    
    # Extract rows (lines after separator)
    rows = []
    for line in lines[separator_idx + 1:]:
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        # Allow rows with same or fewer cells (pad with empty strings)
        while len(cells) < len(headers):
            cells.append('')
        if len(cells) >= len(headers):
            row_dict = dict(zip(headers, cells[:len(headers)]))
            rows.append(row_dict)
    
    return rows


def serialize_table_row(row: Dict[str, str], headers: List[str], table_name: str) -> str:
    """
    Serialize a table row into a sentence format that repeats headers.
    
    Example: "Date: 2024-01-03, Event: Motor vehicle collision, Document: High-Resolution Incident Log, Notes: Single vehicle lost control"
    """
    parts = [f"{header}: {row.get(header, '')}" for header in headers if row.get(header)]
    return ", ".join(parts)


def extract_and_serialize_tables(documents: List[Document]) -> List[TextNode]:
    """
    Detect markdown tables in documents, serialize rows, and create nodes.
    
    Returns a list of TextNode objects, one per table row, with metadata.
    """
    table_nodes = []
    
    for doc in documents:
        text = doc.get_content()
        
        # Find all markdown tables (look for | header | patterns)
        # Match table blocks: header row (optional blank line), separator, data rows
        # Allow blank lines between header and separator
        table_pattern = r'(\|.+\|\n(?:\s*\n)?\|[\s\-\|:]+\|\n(?:\|.+\|\n?)+)'
        tables = re.finditer(table_pattern, text, re.MULTILINE)
        
        # Also try to find table names from preceding headers
        lines = text.split('\n')
        
        for match in tables:
            table_text = match.group(1)
            table_start_pos = match.start()
            
            # Find the table name by looking backwards for a header
            table_name = "Unknown Table"
            # Find which line the table starts on
            text_before = text[:table_start_pos]
            line_num = text_before.count('\n')
            
            # Look backwards from the table for a header (up to 5 lines back)
            for i in range(max(0, line_num - 5), line_num):
                if i < len(lines):
                    line = lines[i]
                    if line.startswith('###') and 'Table' in line:
                        # Extract table name (e.g., "Table 1 — Event Ledger")
                        table_name_match = re.search(r'Table \d+[^—]*—\s*(.+)', line)
                        if table_name_match:
                            table_name = table_name_match.group(1).strip()
                        else:
                            # Fallback: use the header text
                            table_name = line.replace('###', '').strip()
                        break
            
            # Parse the table
            rows = parse_markdown_table(table_text, table_name)
            if not rows:
                continue
            
            # Get headers from first row keys
            headers = list(rows[0].keys()) if rows else []
            
            # Create a node for each row
            for row_idx, row in enumerate(rows):
                row_sentence = serialize_table_row(row, headers, table_name)
                
                # Create node with metadata
                node = TextNode(
                    text=row_sentence,
                    metadata={
                        "node_type": "table_row",
                        "table": table_name,
                        "row_index": row_idx,
                        "source": doc.metadata.get("file_path", "unknown"),
                    }
                )
                table_nodes.append(node)
    
    return table_nodes


def init_llama_settings() -> None:
    """
    Load environment variables and configure the global LlamaIndex settings.
    """
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Create a .env file in the project root with OPENAI_API_KEY=..."
        )

    # Configure LLM + embedding model (adjust models if needed)
    Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0.0)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")

    # Optional global chunk size hint (not critical but fine to set)
    Settings.chunk_size = 1024


def build_indexes():
    """
    Build:
    - hierarchical nodes over the claim timeline
    - a VectorStoreIndex on leaf nodes
    - an AutoMergingRetriever
    - a SummaryIndex over the full documents

    Returns a dict with the main objects.
    """
    init_llama_settings()

    # 1. Load the claim timeline document(s)
    documents = SimpleDirectoryReader(str(DATA_DIR)).load_data()
    if not documents:
        raise RuntimeError(f"No documents found in {DATA_DIR}")

    # 1.5. Extract and serialize markdown tables into row nodes
    table_row_nodes = extract_and_serialize_tables(documents)

    # 2. Build hierarchical nodes (multi-granularity chunking)
    # Default chunk sizes roughly: [2048, 512, 128] – we make them explicit.
    node_parser = HierarchicalNodeParser.from_defaults(
        chunk_sizes=[1024, 512, 128]
    )
    nodes = node_parser.get_nodes_from_documents(documents)

    # Leaf nodes are the smallest chunks; these will be embedded.
    leaf_nodes = get_leaf_nodes(nodes)
    
    # Add table row nodes to leaf nodes (they are already atomic units)
    leaf_nodes.extend(table_row_nodes)

    # 3. Set up storage + base vector index on leaf nodes
    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(nodes)
    # Also add table row nodes to docstore
    if table_row_nodes:
        storage_context.docstore.add_documents(table_row_nodes)

    base_index = VectorStoreIndex(
        leaf_nodes,
        storage_context=storage_context,
    )

    base_retriever = base_index.as_retriever(similarity_top_k=6)

    # 4. Auto-merging retriever: replaces many tiny chunks
    #    with their parents when that’s more coherent.
    auto_merging_retriever = AutoMergingRetriever(
        base_retriever,
        storage_context=storage_context,
        verbose=True,
    )

    # 5. Summary index over the whole documents
    #    (used later by the Summarization Agent).
    summary_index = SummaryIndex.from_documents(documents)

    return {
        "storage_context": storage_context,
        "documents": documents,
        "nodes": nodes,
        "leaf_nodes": leaf_nodes,
        "base_index": base_index,
        "auto_retriever": auto_merging_retriever,
        "summary_index": summary_index,
    }

def get_query_engines():
    """
    Convenience helper:
    - builds indexes
    - returns two query engines:
      * summary_engine: for high-level / timeline questions
      * needle_engine: for precise, 'needle-in-haystack' questions
    """
    idx = build_indexes()

    # High-level summary engine over the SummaryIndex
    summary_engine = idx["summary_index"].as_query_engine(
        response_mode="tree_summarize"
    )

    # Needle engine over the auto-merging retriever
    needle_engine = RetrieverQueryEngine.from_args(
        idx["auto_retriever"],
        response_mode="compact",
    )

    return {
        "summary_engine": summary_engine,
        "needle_engine": needle_engine,
    }

if __name__ == "__main__":
    idx = build_indexes()
    print("✅ Indexes built successfully.")
    print(f"- Documents loaded: {len(idx['documents'])}")
    print(f"- Total nodes:      {len(idx['nodes'])}")
    print(f"- Leaf nodes:       {len(idx['leaf_nodes'])}")
