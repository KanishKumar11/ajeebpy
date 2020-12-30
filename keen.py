import pyttsx3
import datetime
import speech_recognition as sr
import wikipedia
import webbrowser
import pywhatkit
from youtube_search import YoutubeSearch

engine = pyttsx3.init()
engine.setProperty("rate", 150)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[2].id)



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
        
    speak("I am Mr. Ajeeb sir. I am created by Keen Kanish. How may I Help You?")
    
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
            webbrowser.open("https://www.youtube.com")
            
        elif 'open google' in query:
            webbrowser.open("https://www.google.com")
            
        elif 'the time' in query:
            strTime = datetime.datetime.now().strftime("%H:%M:%S")    
            speak(f"Sir, the time is {strTime}")
            
        else:
            pass   

