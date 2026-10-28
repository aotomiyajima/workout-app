from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import math
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
        reps INTEGER,
        sets INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # 既存の投稿はNULL（未設定）のまま、新しい列だけ追加する。
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(workouts)")}
        for column in ("reps", "sets"):
            if column not in columns:
                conn.execute(f"ALTER TABLE workouts ADD COLUMN {column} INTEGER")
        conn.commit()
    finally:
        conn.close()

#アプリ起動時にテーブルを準備
init_db()


def validate_workout(form):
    """登録と編集で共通の入力チェック。元の入力はフォーム表示に使う。"""
    errors = []
    values = {"workout_name": form.get("workout_name", "").strip()}
    if not values["workout_name"]:
        errors.append("種目名を入力してください。")
    try:
        values["weight"] = float(form.get("weight", ""))
        if not math.isfinite(values["weight"]) or values["weight"] < 0:
            raise ValueError
    except ValueError:
        errors.append("重量は0以上の数値で入力してください。")

    for name, label in (("reps", "回数"), ("sets", "セット数")):
        try:
            value = int(form.get(name, ""))
            if value < 1 or value > 9223372036854775807:
                raise ValueError
            values[name] = value
        except ValueError:
            errors.append(f"{label}は1以上の整数で入力してください（SQLiteで保存できる範囲）。")
    return values, errors


@app.route("/",methods=["GET","POST"])
def home():
    form = request.form if request.method == "POST" else {}
    errors = []
    if request.method == "POST":
        values, errors = validate_workout(form)
        if not errors:
            conn = get_db_connection()
            try:
                conn.execute(
                    "INSERT INTO workouts (workout_name,weight,reps,sets) VALUES(?,?,?,?)",
                    (values["workout_name"], values["weight"], values["reps"], values["sets"])
                )
                conn.commit()
            finally:
                conn.close()
            return redirect(url_for("home"))

    conn = get_db_connection()
    try:
        workouts = conn.execute(
            """
            SELECT id,workout_name,weight,reps,sets,created_at
            FROM workouts
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    return render_template("index.html",workouts=workouts,form=form,errors=errors), 400 if errors else 200

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
            values, errors = validate_workout(request.form)
            if errors:
                return render_template("edit.html",workout=request.form,errors=errors),400

            conn.execute(
                """
                UPDATE workouts
                SET workout_name = ?,weight = ?,reps = ?,sets = ?
                WHERE id = ?
                """,
                (values["workout_name"],values["weight"],values["reps"],values["sets"],workout_id)
            )
            conn.commit()

            return redirect(url_for("home"))
        

    finally:
        conn.close()


    return render_template("edit.html",workout=dict(workout))
