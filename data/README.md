# Data Storage (Data)

The `data/` directory is no longer used for primary task persistence in the system.

## Source of Truth
Historical CSV data (like `tasks.csv`) has been deprecated. All tasks and relationships are now stored in **Neo4j** for graph-based dependency management and vector search. 

## Current Role
Currently, this directory provides a persistent location for auxiliary files or session data. For the graph database's persistent volumes, please check the infrastructure definitions in `/db`.
