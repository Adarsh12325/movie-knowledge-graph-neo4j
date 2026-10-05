// queries/delete_movie.cypher
// Core Requirement 9: Safely detach and delete the placeholder movie node

MATCH (m:Movie {title: 'To Be Deleted'})
DETACH DELETE m;
