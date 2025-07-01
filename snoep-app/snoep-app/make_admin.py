from app import app, db, User

email = "debroeder2011@gmail.com"

with app.app_context():
    user = User.query.filter_by(email=email).first()

    if user:
        user.role = 'beheerder'  # Zet de rol naar beheerder
        db.session.commit()
        print(f"{email} is nu admin!")
    else:
        print("Gebruiker niet gevonden.")
