// queries/analytics_degree.cypher
// Core Requirement 10: Degree Centrality Analysis - Top 5 most connected people

MATCH (p:Person)-[r]-()
RETURN p.name AS name, count(r) AS degree
ORDER BY degree DESC, name ASC
LIMIT 5;
