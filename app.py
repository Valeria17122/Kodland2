import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import requests
import hashlib

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Modifica con una chiave segreta

# Funzione per connettersi al database
DB_PATH = "/home/Vale12/Kodland/quiz.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Funzione per ottenere il meteo
def get_weather(city):
    api_key = 'e4d7d2dae7cf4dffb10170023250703'
    url = f'http://api.weatherapi.com/v1/forecast.json?q={city}&days=3&key={api_key}'

    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 or "error" in data:
        return {"cod": "404", "message": data.get("error", {}).get("message", "Errore sconosciuto")}

    # Otteniamo la data corrente e il giorno della settimana
    today_date = datetime.strptime(data['forecast']['forecastday'][0]['date'], "%Y-%m-%d")
    today_weekday = today_date.strftime("%A")  # Nome del giorno della settimana

    # Estrazione dei dati meteo
    weather_info = {
        'weekday': today_weekday,
        'temp_day': data['forecast']['forecastday'][0]['day']['maxtemp_c'],  # Temp max
        'temp_night': data['forecast']['forecastday'][0]['day']['mintemp_c'],  # Temp min
        'forecast': [
            {
                'day': datetime.strptime(day['date'], "%Y-%m-%d").strftime("%A"),
                'temp_day': day['day']['maxtemp_c'],
                'temp_night': day['day']['mintemp_c'],
                'weather': day['day']['condition']['text']
            }
            for day in data['forecast']['forecastday']
        ]
    }

    return weather_info


# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Pagina di login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM User WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            return redirect(url_for('quiz'))
        else:
            return 'Invalid username or password'

    return render_template('login.html')

# Pagina di registrazione
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        nickname = request.form['nickname']

        # Hash della password prima di salvarla nel database
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        conn.execute('INSERT INTO User (username, password, nickname) VALUES (?, ?, ?)',
                     (username, hashed_password, nickname))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# Quiz Page
import random  # Importa il modulo random per mescolare le domande

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Recuperiamo le domande dal database
    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM Question').fetchall()
    conn.close()

    # Inizializziamo l'indice della domanda se non esiste
    index = session.get('question_index', 0)  # Se non esiste, parte da 0
    session['question_index'] = index  # Assicuriamoci che venga impostato

    # Se l'utente ha completato il quiz, reindirizzalo alla pagina dei risultati
    if index >= len(questions):
        return redirect(url_for('result'))

    current_question = questions[index]

    if request.method == 'POST':
        user_answer = request.form.get('answer')
        if user_answer == current_question['answer']:
            session['score'] = session.get('score', 0) + 10  # Inizializza score se non esiste

        session['question_index'] += 1  # Passiamo alla domanda successiva

        return redirect(url_for('quiz'))  # Ricarichiamo la pagina per mostrare la prossima domanda

    return render_template('quiz.html', question=current_question, index=index + 1, total=len(questions))


# Pagina dei risultati con classifica
@app.route('/result')
def result():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    score = session.get('score', 0)

    conn = get_db_connection()
    conn.execute('UPDATE User SET score = score + ? WHERE id = ?', (score, user_id))
    conn.commit()

    user = conn.execute('SELECT * FROM User WHERE id = ?', (user_id,)).fetchone()
    leaderboard = conn.execute('SELECT nickname, score FROM User ORDER BY score DESC').fetchall()
    conn.close()

    session.pop('question_index', None)
    session.pop('score', None)

    return render_template('result.html', user=user, leaderboard=leaderboard, enumerate=enumerate)

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

# Funzione per ottenere i dettagli del meteo
@app.route('/weather', methods=['POST'])
def weather():
    city = request.form['city']
    weather_info = get_weather(city)

    if 'cod' in weather_info and weather_info['cod'] == "404":
        return f"City not found! Error: {weather_info['message']}"

    return render_template('index.html', weather_info=weather_info)

if __name__ == '__main__':
    app.run(debug=True)
