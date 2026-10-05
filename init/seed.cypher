// init/seed.cypher
// Movie Knowledge Graph - Initial Schema Constraints and Seed Data
// Optimized for idempotent startup execution in Neo4j 5.x

// ==========================================
// 1. Schema Constraints for Data Integrity
// ==========================================
CREATE CONSTRAINT movie_title IF NOT EXISTS FOR (m:Movie) REQUIRE m.title IS UNIQUE;
CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE;

// ==========================================
// 2. Genre Nodes
// ==========================================
MERGE (:Genre {name: 'Sci-Fi'});
MERGE (:Genre {name: 'Action'});

// ==========================================
// 3. Movies and People Entities
// ==========================================
MERGE (matrix:Movie {title: 'The Matrix', released: 1999, tagline: 'Welcome to the Real World'});
MERGE (keanu:Person {name: 'Keanu Reeves', born: 1964});
MERGE (carrie:Person {name: 'Carrie-Anne Moss', born: 1967});
MERGE (laurence:Person {name: 'Laurence Fishburne', born: 1961});
MERGE (hugo:Person {name: 'Hugo Weaving', born: 1960});
MERGE (lana:Person {name: 'Lana Wachowski', born: 1965});
MERGE (lilly:Person {name: 'Lilly Wachowski', born: 1967});
MERGE (joel:Person {name: 'Joel Silver', born: 1952});

// ==========================================
// 4. Relationships for "The Matrix"
// ==========================================
MERGE (matrix)-[:HAS_GENRE]->(:Genre {name: 'Sci-Fi'});
MERGE (keanu)-[:ACTED_IN {roles: ['Neo']}]->(matrix);
MERGE (carrie)-[:ACTED_IN {roles: ['Trinity']}]->(matrix);
MERGE (laurence)-[:ACTED_IN {roles: ['Morpheus']}]->(matrix);
MERGE (hugo)-[:ACTED_IN {roles: ['Agent Smith']}]->(matrix);
MERGE (lana)-[:DIRECTED]->(matrix);
MERGE (lilly)-[:DIRECTED]->(matrix);
MERGE (joel)-[:PRODUCED]->(matrix);

// ==========================================
// 5. Additional Movie for Multi-Movie Queries
// ==========================================
MERGE (jwick:Movie {title: 'John Wick', released: 2014, tagline: 'Don\'t set him off.'});
MERGE (jwick)-[:HAS_GENRE]->(:Genre {name: 'Action'});
MERGE (keanu)-[:ACTED_IN {roles: ['John Wick']}]->(jwick);

// ==========================================
// 6. Test Movie for Deletion Operations
// ==========================================
MERGE (:Movie {title: 'To Be Deleted', released: 2024});
