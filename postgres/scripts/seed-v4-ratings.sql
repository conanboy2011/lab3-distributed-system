\connect ratings

CREATE TABLE IF NOT EXISTS rating (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL,
    stars INTEGER NOT NULL DEFAULT 1
);

INSERT INTO rating (
    username,
    stars
)
VALUES (
    'conanboy2011',
    75
);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO program;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO program;
GRANT USAGE, CREATE ON SCHEMA public TO program;