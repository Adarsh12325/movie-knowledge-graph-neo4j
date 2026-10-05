// queries/create_movie.cypher
// Core Requirement 5: Create movie 'V for Vendetta' and link Hugo Weaving via ACTED_IN

MERGE (m:Movie {title: 'V for Vendetta'})
ON CREATE SET m.released = 2005, m.tagline = 'Freedom! Forever!'
WITH m
MATCH (hugo:Person {name: 'Hugo Weaving'})
MERGE (hugo)-[:ACTED_IN {roles: ['V']}]->(m)
WITH m
MATCH (lana:Person {name: 'Lana Wachowski'})
MERGE (lana)-[:PRODUCED]->(m)
WITH m
MATCH (lilly:Person {name: 'Lilly Wachowski'})
MERGE (lilly)-[:PRODUCED]->(m)
RETURN m.title AS title, m.released AS released;
