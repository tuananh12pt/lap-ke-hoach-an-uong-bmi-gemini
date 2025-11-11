from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import os

from . import utils
from .gemini_client import GeminiClient

load_dotenv()

app = Flask(__name__)

gemini = GeminiClient(api_key=os.getenv('' \
''), api_url=os.getenv('GEMINI_API_URL'))


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/plan', methods=['POST'])
def plan():
    # Read form
    weight = float(request.form.get('weight'))
    height = float(request.form.get('height'))
    age = int(request.form.get('age'))
    sex = request.form.get('sex', 'male')
    activity = request.form.get('activity', 'sedentary')
    goal = request.form.get('goal', 'auto')
    units = request.form.get('units', 'metric')
    diet = request.form.get('diet', 'none')

    if units == 'imperial':
        # convert lbs/in to kg/cm
        weight = utils.lbs_to_kg(weight)
        height = utils.inches_to_cm(height)

    bmi = utils.calculate_bmi(weight, height)
    tdee = utils.estimate_tdee(weight, height, age, sex, activity)
    target_cal = utils.target_calories_by_goal(tdee, bmi, goal)

    prompt = utils.build_prompt(bmi=bmi, tdee=tdee, target_cal=target_cal, diet=diet, goal=goal, activity=activity)

    # Ask Gemini (or mock)
    response_text = gemini.generate(prompt)

    return render_template('plan.html', bmi=round(bmi,1), tdee=int(tdee), target_cal=int(target_cal), plan_text=response_text)


if __name__ == '__main__':
    app.run(debug=True)
