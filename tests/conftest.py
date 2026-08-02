import sys
import os

# Make sure our gateway and rag-core code can be imported from test files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "gateway"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag-core"))