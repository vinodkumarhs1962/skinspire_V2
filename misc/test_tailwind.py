from flask import Flask, render_template

app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')

@app.route('/tailwind-test')
def tailwind_test():
    return render_template('test/tailwind_test.html')

if __name__ == '__main__':
    app.run(debug=True, port=5050)