DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS album;
DROP TABLE IF EXISTS photo;
DROP TABLE IF EXISTS comment;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT unique NOT NULL,
  hash TEXT NOT NULL
);

CREATE TABLE album (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  created_on DATETIME NOT NULL,
  created_by INTEGER NOT NULL,
  hash TEXT NOT NULL,
  FOREIGN KEY (created_by) REFERENCES user (id)
);

CREATE TABLE photo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  created_on DATETIME NOT NULL,
  created_by INTEGER NOT NULL,
  location TEXT NOT NULL,
  FOREIGN KEY (created_by) REFERENCES user (id)
);

CREATE TABLE comment (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  comment TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE user_album (
  user_id INTEGER NOT NULL,
  album_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id),
  FOREIGN KEY (album_id) REFERENCES album (id)
);

CREATE TABLE album_photo (
  album_id INTEGER NOT NULL,
  photo_id INTEGER NOT NULL,
  FOREIGN KEY (album_id) REFERENCES album (id),
  FOREIGN KEY (photo_id) REFERENCES photo (id)
);

CREATE TABLE album_comment (
  album_id INTEGER NOT NULL,
  comment_id INTEGER NOT NULL,
  FOREIGN KEY (album_id) REFERENCES album (id),
  FOREIGN KEY (comment_id) REFERENCES comment (id)
);
