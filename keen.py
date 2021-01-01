# This v1.0 of Mr. Ajeeb Created by Keen Kanish
# All imports here
import pyttsx3 #Text-to-speech
import datetime #To get date and time
import speech_recognition as sr #To recognise speech of user
import wikipedia #To get content from wikipedia
import webbrowser #To open links in browser
import pywhatkit #To play songs on youtube
import pyaudio #With this our AI robot will speak
import pyjokes
import random
import calendar
import warnings
from gtts import gTTS
from kivy.app import App
from kivy.uix.button import Button

#Ignore any warning message
warnings.filterwarnings('ignore')

engine = pyttsx3.init()
engine.setProperty("rate", 120)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[2].id)




class Ajeeb(App):
    def build(self):
        return Button(text='This is Mr. Ajeeb Please Close this window to continue')

Ajeeb().run()


def speak(audio):
    engine.say(audio)
    engine.runAndWait()

def wishMe():
    hour = int(datetime.datetime.now().hour)
    if hour>=0 and hour<12:
        speak("Good Morning!")
    
    elif hour>=12 and hour<18:
        speak("Good Afternoon!")
        
    else:
        speak("Good Evening!")
        
    speak("I am Mr. Ajeeeb.I was created by Keen Kanish. How can i help you?")
    
def takeCommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("listening...")
        r.pause_threshold = 1
        audio = r.listen(source)
        
    try:
        print("Recogninzing...")
        query = r.recognize_google(audio, language='en-in')
        print(f"You said: {query}\n")

    except Exception:
        print("Say that again please...")
        return  "None"
    return query

def date():
    year = int(datetime.datetime.now().year)
    month = str(datetime.datetime.now().month)
    date = int(datetime.datetime.now().day)
    speak(date)
    speak(month)
    speak(year)
    print(date)
    print(month)
    print(year)
    
    
if __name__ == "__main__":
    speak("Kanish is Keen!")
    
    wishMe()
    while True:
        query = takeCommand().lower()
        
        if 'wikipedia' in query:
            speak('Searching on wikipedia...')
            query = query.replace("wikipedia", "")
            results = wikipedia.summary(query, sentences=2)
            print(results)
            speak("According to wikipedia" + results)
            
        elif 'date' in query:
            date()
    
        elif 'play' in query:
            speak('Playing...')
            query = query.replace(" youtube", "")
            speak( query)
            results = pywhatkit.playonyt(query)
        
        elif 'open youtube' in query:
            speak("Opening youtube...")
            webbrowser.open("https://www.youtube.com")

            
        elif 'open google' in query:
            speak("Opening Google...")
            webbrowser.open("https://www.google.com")
            
        elif 'the time' in query:
            strTime = datetime.datetime.now().strftime("%H:%M:%S")    
            speak(f"Sir, the time is {strTime}")
            print(f"Sir, the time is {strTime}")
            
        elif 'thank you' in query:
            speak("Oh! That's my pleasure!")
            print("Oh! That's my pleasure!")
        
        elif 'thanks' in query:
            speak("Oh! That's my pleasure!")
            print("Oh! That's my pleasure!")
            
        elif 'relationship' in query:
            speak("Yes! I am in realtionship with wifi")       
            print("Yes! I am in realtionship with wifi")
            
        elif 'your name' in query:
            speak("My name is Mr. Ajeeb")        
            print("My name is Mr. Ajeeb")   
            
        elif 'your age' in query:
            speak("I was created on 30st December 2020. So you can calculate it yourself")         
            print("I was created on 30st December 2020. So you can calculate it yourself")
            
        elif 'old' in query:
            speak("I was created on 30st December 2020. So you can calculate it yourself")         
            print("I was created on 30st December 2020. So you can calculate it yourself")    
            
        elif 'joke' in query:
             speak("Grinding it" + pyjokes.get_joke())
             print("Grinding it" + pyjokes.get_joke())
                      
        else:
            pass   



