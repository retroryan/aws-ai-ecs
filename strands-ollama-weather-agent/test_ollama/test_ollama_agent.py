"""
Test Ollama Agent - Based on AWS Strands Ollama Sample

This script demonstrates how to create a local agent using Strands and Ollama.
The agent is capable of performing file operations and simple tasks.
"""

import os
import requests
from strands import Agent, tool
from strands.models.ollama import OllamaModel


# File Operation Tools
@tool
def file_read(file_path: str) -> str:
    """Read a file and return its content.

    Args:
        file_path (str): Path to the file to read

    Returns:
        str: Content of the file

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found."
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def file_write(file_path: str, content: str) -> str:
    """Write content to a file.

    Args:
        file_path (str): The path to the file
        content (str): The content to write to the file

    Returns:
        str: A message indicating success or failure
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        with open(file_path, "w") as file:
            file.write(content)
        return f"File '{file_path}' written successfully."
    except Exception as e:
        return f"Error writing to file: {str(e)}"


@tool
def list_directory(directory_path: str = ".") -> str:
    """List files and directories in the specified path.

    Args:
        directory_path (str): Path to the directory to list

    Returns:
        str: A formatted string listing all files and directories
    """
    try:
        items = os.listdir(directory_path)
        files = []
        directories = []

        for item in items:
            full_path = os.path.join(directory_path, item)
            if os.path.isdir(full_path):
                directories.append(f"Folder: {item}/")
            else:
                files.append(f"File: {item}")

        result = f"Contents of {os.path.abspath(directory_path)}:\n"
        result += (
            "\nDirectories:\n" + "\n".join(sorted(directories))
            if directories
            else "\nNo directories found."
        )
        result += (
            "\n\nFiles:\n" + "\n".join(sorted(files)) if files else "\nNo files found."
        )

        return result
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def check_ollama_connection():
    """Check if Ollama is running and list available models."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        print("✅ Ollama is running. Available models:")
        for model in response.json().get("models", []):
            print(f"- {model['name']}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Ollama is not running. Please start Ollama before proceeding.")
        print("Run: ollama serve")
        return False


def create_ollama_agent(model_id: str = "llama3.2:1b"):
    """Create an Ollama-powered agent with file operation tools."""
    
    # Define a comprehensive system prompt
    system_prompt = """
    You are a helpful personal assistant capable of performing local file actions and simple tasks for the user.

    Your key capabilities:
    1. Read, understand, and summarize files.
    2. Create and write to files.
    3. List directory contents and provide information on the files.
    4. Summarize text content

    When using tools:
    - Always verify file paths before operations
    - Be careful with system commands
    - Provide clear explanations of what you're doing
    - If a task cannot be completed, explain why and suggest alternatives

    Always be helpful, concise, and focus on addressing the user's needs efficiently.
    """

    # Configure the Ollama model
    ollama_model = OllamaModel(
        model_id=model_id,
        host="http://localhost:11434",
        params={
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": True,
        },
    )

    # Create the agent
    agent = Agent(
        system_prompt=system_prompt,
        model=ollama_model,
        tools=[file_read, file_write, list_directory],
    )
    
    return agent


def test_basic_operations():
    """Test basic agent operations."""
    if not check_ollama_connection():
        return
    
    print("\n🚀 Creating Ollama agent...")
    agent = create_ollama_agent()
    
    # Test 1: List current directory
    print("\n📁 Test 1: List files in test_ollama directory")
    response = agent("Show me the files in the current directory")
    print(f"Response: {response}")
    
    # Test 2: Create a sample file
    print("\n📝 Test 2: Create a sample file")
    response = agent(
        "Create a file called 'test_output.txt' with the content 'This is a test file created by the Ollama agent.'"
    )
    print(f"Response: {response}")
    
    # Test 3: Read the file back
    print("\n📖 Test 3: Read the created file")
    response = agent("Read the file 'test_output.txt' and tell me what it contains")
    print(f"Response: {response}")
    
    # Test 4: Create a summary
    print("\n📊 Test 4: Create a README")
    response = agent(
        "Create a README.md file that describes this test_ollama directory and what we've done here"
    )
    print(f"Response: {response}")


def test_weather_related_query():
    """Test if the Ollama agent can handle weather-related queries (without tools)."""
    if not check_ollama_connection():
        return
    
    print("\n🌤️ Testing weather-related query handling...")
    agent = create_ollama_agent()
    
    response = agent(
        "If I were to build a weather agent, what kind of data would I need to collect? "
        "Write your answer to a file called 'weather_agent_planning.md'"
    )
    print(f"Response: {response}")


if __name__ == "__main__":
    print("=== Ollama Agent Test Suite ===\n")
    
    # Run basic tests
    test_basic_operations()
    
    # Run weather-related test
    test_weather_related_query()
    
    print("\n✅ All tests completed!")