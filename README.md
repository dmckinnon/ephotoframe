# ephotoframe
Code for a raspberry pi to sync a google photos album and display the images on a screen

## The setup
+ Raspberry Pi 3B+ (though virtually any pi will work here)
+ spare keyboard, unless you have SSH set up
+ external monitor (I'm using a 15" Viewsonic)
+ motion sensor, [for example](https://www.adafruit.com/product/189)

### Google Cloud
I'm using a google photos album to store all the photos and allow others to add. To access this with code, you need to set up google photos api in google cloud for your account.

This is basically a rewrite/expansion of what I found here: https://github.com/polzerdo55862/google-photos-api/blob/main/Google_API.ipynb

Head to Google cloud at console.cloud.google.com. Create a new project, with default settings.

First, add the Google photos library API. Click APIs and Services in the left bar, search for 'photos', and click 'Enable' on Google Photos Library API. 
Next, go to OAuth Consent Screen. Head to Audience, and add yourself as a user. Make sure the User Type is External. Then go to Clients. Add a client, as a 'Desktop app'. This will be your python program. This creates a json file with credentials. Download this and give it a sensible name, like `credentials.json`.
Finally, under 'Data Access', add the scope of `.../auth/photoslibrary.readonly`.

### Python
Get the ID of the album you want and add it to the python script, under ALBUM_ID - you can get this from the URL of the album. 



