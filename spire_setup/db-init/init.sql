CREATE USER spire WITH PASSWORD 'spire-secret';
CREATE DATABASE spire OWNER spire;
\c spire;
GRANT ALL ON SCHEMA public TO spire;