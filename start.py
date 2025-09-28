import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    # Import and run the agent
    import agent
    # The agent.py file already has the main execution code at the bottom