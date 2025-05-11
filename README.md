# A Homemade Digital Photo frame
This repo contains code that will - with the right accessories - sync with a Google Photos Album and display all the images in random order on a screen as a digital photo frame. 

Why am I doing this instead of buying one? Several reasons:
- Security: I don't want to give some random company my google account details so they can sync with the album. What if the device has poor security, what if the company does, etc
- Maintainability: I bought a digital photo frame, and it didn't perform precisely as a wanted and then developed issues. I'd like the control to fix or change things as desired
- I could have a simpler offline one, but I want to use a Google photos album so multiple people can add photos
- fun project

## The setup
+ Raspberry Pi 3B+ (though virtually any pi will work here, or any relatively modern computer)
+ spare keyboard, unless you have SSH set up (really just to make things easier)
+ external monitor (I'm using a 15" Viewsonic)
+ motion sensor, [for example](https://www.adafruit.com/product/189)

## Getting this working
This was trickier than I expected, with two main causes: google cloud, and turning the Pi display off. Everything else was pretty straightforward. 90% of the code comes from ChatGPT, with tweaks from me where it was hallucinating/out of date.

### Google Cloud
I'm using a google photos album to store all the photos and allow others to add. To access this with code, you need to set up google photos api in google cloud for your account.

This is basically a rewrite/expansion of what I found here: https://github.com/polzerdo55862/google-photos-api/blob/main/Google_API.ipynb

Head to Google cloud at console.cloud.google.com. Create a new project, with default settings.
First, add the Google photos library API. Click APIs and Services in the left bar, search for 'photos', and click 'Enable' on Google Photos Library API. 
Next, go to OAuth Consent Screen. Head to Audience, and add yourself as a user. Make sure the User Type is External. Then go to Clients. Add a client, as a 'Desktop app'. This will be your python program. This creates a json file with credentials. Download this and give it a sensible name, like `credentials.json`.
Finally, under 'Data Access', add the scope of `.../auth/photoslibrary.readonly`.

You need the ID of the album you want to sync. This is not the name, but rather the jumble of characters in the URL, eg. https://photos.google.com/share/This-entire-bit-here?key=no-don't-grab-this-bit.
Note the '?key=' - the ID is everything _before_ that. 

See [fetch_album_items](https://github.com/dmckinnon/ephotoframe/blob/d01b2185efdde8d2210a72bc008690fc1ff7d432/slideshow.py#L78) for how to do a post request and get the photos (shouldn't this be a get? Guess not, this worked). Then follows [downloading the images](https://github.com/dmckinnon/ephotoframe/blob/d01b2185efdde8d2210a72bc008690fc1ff7d432/slideshow.py#L95) and this also performs the extra step of conversion in case of HEIC. This is only necessary because pygame cannot display HEIC images, and I couldn't get the libraries to make it display HEIC working, so I just convert to JPEG. For this, you'll need to install magick (`sudo apt install magick`).

One final call-out is the caching of credentials - instead of having to authenticate each time, I cache the credentials locally so that it auto signs in. 

### Sleeping the display
My previous digital photo frame displayed photos for 15 minutes after motion, and if no motion was detected in that time span, it would turn its display off. I wanted something similar - after a time, don't show anything. But then, if motion is detected again, start showing and repeat the process. 

The motion sensor setup is quite easy - connect this to a pin and if there is a HIGH spike on the pin, there's your motion. There's [loads](https://learn.adafruit.com/pir-passive-infrared-proximity-motion-sensor) of [articles](https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://projects.raspberrypi.org/en/projects/physical-computing/11&ved=2ahUKEwi_sarogJyNAxUiLzQIHRTDLj4QFnoECAkQAQ&usg=AOvVaw38AY7FunQUMHMzu2kj07sY) [written](https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://www.electronicwings.com/raspberry-pi/pir-motion-sensor-interfacing-with-raspberry-pi&ved=2ahUKEwi_sarogJyNAxUiLzQIHRTDLj4QFnoECB0QAQ&usg=AOvVaw0jnPXSIdr3lS-FK5Ve9Oqv) about PIR sensors. 

The hard bit is the display sleep. ChatGPT gave me multiple ways to turn a display off, and they all basically worked:
- vcgencmd display_power 0
- tvservice -o
- xset dpms --force off

But then when I tried to turn the display _on_ again ... it seems like the display had turned off so hardcore that a simple command could not do it? I could activate the power LED, but it still wouldn't display anything. 
To cut a long story short, I couldn't figure out a solution here with what I specifically wanted. 
So my workaround is: configure the actual display settings on the monitor to sleep after 15 minutes of inactvity, and then use a blank screensaver on the raspberry pi with [xscreensaver](https://pimylifeup.com/raspberry-pi-screensaver/). The idea here is that the python script can activate the screensaver itself from code after some time, and then the display unit will detect nothing for a period (the nothing being the screensaver) and sleep. When the pi wakes, the display receives something, and wakes up. 


