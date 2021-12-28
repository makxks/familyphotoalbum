# Family Photo Album
#### Video Demo:  https://youtu.be/T1xa8gCK00k
#### Description:
Flask app to share photo albums - primarily for sharing with family.
  
Inspired by my own situation of living away from most of my family and being unable to visit for an extended period due to COVID. My final project is a flask web app to easily share photos with other users, and non-users of the site.

Using the same utilities built into Flask as used earlier in CS50, users can register and log in to the site. For new users they will see no photo albums, returning users will see any created or received albums at this point.

Users can create their own albums to which they can upload photos. Upon creation of an album users give the album a "share password" this password can be used later to share to non-users of the site, so that they are also able to view the photos users wish to share. During upload of photos, the images are resized by the Pillow Python library so as not to take up too much space, as it is then saved locally to the server the web app is being hosted on (currently on python anywhere as below).

Users also have the option to edit albums (the title of the album and the share password can be changed), to edit photos (the title of the image, and the rotation of the image can be changed), and to delete albums or photos if desired. For signed in users there is also the option to comment on photo albums, leaving messages among the users able to view the album.

Albums can be shared with users directly via a share option. They can also be shared to non-users through one of two specific generated links. The first generated link uses 2 hashes and checks both when the link is used, and the second needs to be edited by the user to include the "share password" as the final parameter of the link that is then checked against the stored hash.

Individual photos can also be shared, but only to individual users due to how the database is structured currently. The workaround is to create an album containing just that one photo and share to non-users that way.

The app is written in Flask, and the data is stored in a sqlite3 database.

Can be used locally by setting FLASK_ENV to 'development' and FLASK_APP to 'flaskr' and making sure all required modules are installed then just starting up with 'flask run'

Can be found online at http://maxplatt.pythonanywhere.com/

Note: the code that is used to host the site on python anywhere is slightly different as the requirements for hosting are slightly different there than for a local project running with flask run
