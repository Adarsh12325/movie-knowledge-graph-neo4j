// queries/find_co_actors.cypher
// Core Requirement 7: Find all co-actors of Hugo Weaving in 'The Matrix' (excluding Hugo Weaving)

MATCH (hugo:Person {name: 'Hugo Weaving'})-[:ACTED_IN]->(m:Movie {title: 'The Matrix'})<-[:ACTED_IN]-(coActor:Person)
WHERE coActor <> hugo
RETURN DISTINCT coActor.name AS name
ORDER BY name ASC;
