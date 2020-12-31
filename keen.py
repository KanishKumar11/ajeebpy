# This v1.0 of Mr. Ajeeb Created by Keen Kanish
import pyttsx3
import datetime
import speech_recognition as sr
import wikipedia
import webbrowser
import pywhatkit
import pyaudio
import pyjokes

engine = pyttsx3.init()
engine.setProperty("rate", 150)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[2].id)


from kivy.app import App
from kivy.uix.button import Button

class TestApp(App):
    def build(self):
        return Button(text='This is Mr. Ajeeb Please Close this window to continue')

TestApp().run()


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
        
    speak("I am Mr. Ajeeb sir. I was created by Keen Kanish. How may I Help You?")
    
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



