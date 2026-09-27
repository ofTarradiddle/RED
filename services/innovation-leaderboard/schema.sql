CREATE TABLE IF NOT EXISTS innovation_scores (
    dataset_id TEXT NOT NULL,
    run_hash TEXT NOT NULL CHECK(length(run_hash) = 64),
    replay_id TEXT NOT NULL,
    display_name TEXT NOT NULL CHECK(length(display_name) BETWEEN 1 AND 20),
    score_value REAL NOT NULL CHECK(score_value >= 0),
    score_change REAL NOT NULL CHECK(score_change >= -1),
    decisions INTEGER NOT NULL CHECK(decisions >= 0 AND decisions <= 2000),
    benchmark_value REAL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    actions_json TEXT NOT NULL CHECK(length(actions_json) <= 65536),
    submitted_at TEXT NOT NULL,
    PRIMARY KEY(dataset_id, run_hash)
) STRICT;

CREATE INDEX IF NOT EXISTS innovation_scores_ranking
ON innovation_scores(dataset_id, score_value DESC, submitted_at ASC, run_hash ASC);
