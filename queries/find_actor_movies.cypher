// queries/find_actor_movies.cypher
// Core Requirement 6: Find all movies acted in by Keanu Reeves

MATCH (p:Person {name: 'Keanu Reeves'})-[:ACTED_IN]->(m:Movie)
RETURN m.title AS title
ORDER BY title ASC;
