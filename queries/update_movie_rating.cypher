// queries/update_movie_rating.cypher
// Core Requirement 8: Add or update rating property to 8.7 on 'The Matrix'

MATCH (m:Movie {title: 'The Matrix'})
SET m.rating = 8.7
RETURN m.title AS title, m.rating AS rating;
