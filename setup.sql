PRAGMA foreign_keys = ON;

CREATE TABLE `Species`(
    `Species_id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `avg_Wingspan` REAL NOT NULL,
    `avg_Lifespan` REAL NOT NULL,
    `diet` TEXT NOT NULL CHECK (`diet` IN ('insects', 'rodents', 'birds', 'seeds', 'fruit', 'fish', 'unknown')),
    `common name` TEXT NOT NULL,
    `scientific name` TEXT NOT NULL
);

CREATE TABLE `users`(
    `user_id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `username` TEXT NOT NULL,
    `date_Joined` TEXT NOT NULL
);

CREATE TABLE `Bird`(
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `Species_id` INTEGER NOT NULL,
    `Name` TEXT NULL,
    FOREIGN KEY (`Species_id`) REFERENCES `Species`(`Species_id`)
);

CREATE TABLE `Bird Sighting`(
    `sighting_id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `bird_id` INTEGER NOT NULL,
    `person_id` INTEGER NOT NULL,
    `location` TEXT NOT NULL,
    `Sighting date` TEXT NOT NULL,
    FOREIGN KEY (`bird_id`) REFERENCES `Bird`(`id`),
    FOREIGN KEY (`person_id`) REFERENCES `users`(`user_id`)
);
