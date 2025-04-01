# Dátová Mapa

A Streamlit application for managing and visualizing hierarchical data using a closure table pattern.

## Project Structure

The project has been refactored into a modular structure:

- `app.py` - Main application entry point
- `models.py` - Data models and operations for the closure table
- `views.py` - UI components for administrator and user views
- `utils.py` - Utility functions for various operations

## Features

- Two modes: Administrator and User
- Tree operations: add, delete, and move nodes
- Visualization of the tree structure using interactive graph and tree components
- File upload/download for closure table data
- Completion score calculation

## Requirements

The application requires the following dependencies:

```
pandas
streamlit
streamlit-agraph
streamlit-tree-select
```

## Running the Application

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Run the Streamlit application:

```bash
streamlit run app.py
```

## Usage

### Administrator Mode

In Administrator mode, you can:
- Add new nodes to the tree
- Delete nodes (and their descendants)
- Move nodes to different parents
- Download the closure table as CSV

### User Mode

In User mode, you can:
- Add your own nodes under existing admin nodes
- Delete your own nodes
- View the combined tree structure
- See the completion score

## Closure Table Pattern

This application uses the closure table pattern to represent hierarchical data. The closure table stores all relationships between nodes, including direct and indirect relationships, making it efficient for querying and manipulating tree structures.
