from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path

app = Flask(__name__)

#app.pyと同じフォルダにデータベースを作る
DATABASE = Path(__file__).with_name("workouts.db")


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS workouts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_name TEXT NOT NULL,
        weight REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
    finally:
        conn.close()

#アプリ起動時にテーブルを準備
init_db()


@app.route("/",methods=["GET","POST"])
def home():
    if request.method == "POST":
        workout_name = request.form.get("workout_name","").strip()
        weight = request.form.get("weight","")

        if not workout_name or not weight:
            return "種目名と重量を入力してください",400

        try:
            weight_value = float(weight)
        except ValueError:
            return "重量は数値で入力してください",400

        if weight_value < 0:
            return "重量は0以上で入力してください",400

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO workouts (workout_name,weight)VALUES(?,?)",
                (workout_name,weight_value)
            )
            conn.commit()
        finally:
            conn.close()
            
        return redirect(url_for("home"))

    conn = get_db_connection()
    try:
        workouts = conn.execute(
            """
            SELECT id,workout_name,weight,created_at
            FROM workouts
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    return render_template("index.html",workouts=workouts)

#削除処理
@app.route("/delete/<int:workout_id>",methods=["POST"])
def delete_workout(workout_id):
    conn = get_db_connection()

    try:
        conn.execute(
            "DELETE FROM workouts WHERE id = ?",
            (workout_id,)
        )
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("home"))

#編集処理
@app.route("/edit/<int:workout_id>",methods=["GET","POST"])
def edit_workout(workout_id):
    conn = get_db_connection()

    try:
        workout = conn.execute(
            "SELECT * FROM workouts WHERE id = ?",
            (workout_id,)
        ).fetchone()

        if workout is None:
            return "投稿が見つかりません",404

        if request.method == "POST":
            workout_name = request.form.get(
                "workout_name",""
            ).strip()
            weight = request.form.get("weight","")

            if not workout_name or not weight:
                return "種目名と重量を入力してください",400

            try:
                weight_value = float(weight)
            except ValueError:
                return "重量は数値で入力してください",400

            if weight_value < 0:
                return "重量は0以上で入力してください",400

            conn.execute(
                """
                UPDATE workouts
                SET workout_name = ?,weight = ?
                WHERE id = ?
                """,
                (workout_name,weight_value,workout_id)
            )
            conn.commit()

            return redirect(url_for("home"))
        

    finally:
        conn.close()


    return render_template("edit.html",workout=workout)