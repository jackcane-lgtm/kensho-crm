import os
import re
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Database config - Railway provides DATABASE_URL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///kensho.db')
# Fix for postgres:// vs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Museum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    website = db.Column(db.String(500))
    address = db.Column(db.String(500))
    personalization = db.Column(db.Text)
    interest = db.Column(db.String(50), default='')
    contacts = db.relationship('Contact', backref='museum_rel', lazy=True)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100))
    title = db.Column(db.String(200))
    museum = db.Column(db.String(200))
    museum_id = db.Column(db.Integer, db.ForeignKey('museum.id'))
    email = db.Column(db.String(200))
    linkedin = db.Column(db.String(500))
    personalization = db.Column(db.Text)
    email_status = db.Column(db.String(50), default='')
    linkedin_status = db.Column(db.String(50), default='')
    reply_status = db.Column(db.String(50), default='')

# Email template
EMAIL_TEMPLATE = '''Dear {name},

As a soon-to-be fourth-year student at the Reinwardt Academy in Amsterdam, part of the Amsterdam University of the Arts, I have spent my studies exploring how cultural heritage connects communities. I am writing to inquire about a six-month internship at {organization} in London, starting this October.

My education focuses on the "biography" of objects and places, and how they serve as bridges between people and perspectives. I consider myself a connector. I thrive in collaborative environments and look beyond physical artifacts to engage broader questions of inclusivity and social relevance.

My passion for heritage has taken me to museums and cultural institutions across 8 countries, and I have participated in heritage documentaries and community events serving diverse audiences. I was also featured in an Amsterdam museum collection celebrating local martial arts schools, where I contributed to the artistic representation of my own school. This allowed me to experience heritage as an active participant, not just an observer.

Currently, I work at the Anne Frank House, where I deliver weekly introductions to international visitors. I independently researched and developed my own presentation materials and learned how to share deeply sensitive history in ways that remain accessible, engaging, and respectful. In addition to presentations, I support museum-wide operations and have gained insight into how a world-class institution serves diverse global audiences.

I am drawn to {organization} because of your commitment to {personalization}. I am proactive, reflective, and eager to bring my perspective on inclusive heritage to your team while continuing to learn from your expertise.

I would welcome the opportunity to discuss how I could contribute to your upcoming projects. Thank you for your time and consideration.

Yours sincerely,
Kensho Koster'''

def extract_first_name(full_name):
    if not full_name:
        return ""
    name = str(full_name).strip()
    prefixes = ['Dr ', 'Dr. ', 'Dame ', 'Prof ', 'Prof. ', 'Sir ']
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
    first = name.split()[0] if name.split() else name
    return first.rstrip('.')

def extract_email(email_field):
    if not email_field:
        return ""
    email_str = str(email_field)
    if '❌' in email_str or 'No Email' in email_str.lower():
        return ""
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email_str)
    return match.group(0) if match else ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/museums')
def get_museums():
    museums = Museum.query.all()
    result = []
    for m in museums:
        positive_replies = Contact.query.filter_by(museum=m.name, reply_status='Positive Reply').count()
        has_contacts = Contact.query.filter_by(museum=m.name).count()
        
        if has_contacts == 0:
            engagement = 'No Contacts'
        elif positive_replies > 0:
            engagement = 'Engaged'
        else:
            engagement = 'Pending'
            
        result.append({
            'id': m.id,
            'name': m.name,
            'website': m.website,
            'address': m.address,
            'personalization': m.personalization,
            'interest': m.interest or '',
            'contact_count': has_contacts,
            'engagement': engagement
        })
    return jsonify(result)

@app.route('/api/museums', methods=['POST'])
def create_museum():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    # Check if exists
    existing = Museum.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'Museum already exists'}), 400
    
    museum = Museum(
        name=name,
        website=data.get('website', ''),
        address=data.get('address', ''),
        personalization=data.get('personalization', ''),
        interest=''
    )
    db.session.add(museum)
    db.session.commit()
    
    return jsonify({'success': True, 'id': museum.id})

@app.route('/api/museums/<int:museum_id>', methods=['PUT'])
def update_museum(museum_id):
    museum = Museum.query.get_or_404(museum_id)
    data = request.json
    if 'interest' in data:
        museum.interest = data['interest']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/contacts')
def get_contacts():
    contacts = Contact.query.all()
    result = []
    for c in contacts:
        # Get personalization - use contact's own or fall back to museum's
        personalization = c.personalization
        if not personalization:
            museum = Museum.query.filter_by(name=c.museum).first()
            if museum:
                personalization = museum.personalization
        
        recipient = c.first_name if c.first_name else 'Hiring Manager'
        email_text = EMAIL_TEMPLATE.format(
            name=recipient,
            organization=c.museum or '[Organization]',
            personalization=personalization or '[specific project or value]'
        )
        
        result.append({
            'id': c.id,
            'name': c.name,
            'first_name': c.first_name,
            'title': c.title,
            'museum': c.museum,
            'email': c.email,
            'linkedin': c.linkedin,
            'personalization': personalization,
            'email_status': c.email_status or '',
            'linkedin_status': c.linkedin_status or '',
            'reply_status': c.reply_status or '',
            'personalized_email': email_text
        })
    return jsonify(result)

@app.route('/api/contacts', methods=['POST'])
def create_contact():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    museum_name = data.get('museum', '').strip()
    museum = Museum.query.filter_by(name=museum_name).first()
    
    # Get personalization - use provided or fall back to museum's
    personalization = data.get('personalization', '').strip()
    if not personalization and museum:
        personalization = museum.personalization
    
    contact = Contact(
        name=name,
        first_name=extract_first_name(name),
        title=data.get('title', ''),
        museum=museum_name,
        museum_id=museum.id if museum else None,
        email=data.get('email', ''),
        linkedin=data.get('linkedin', ''),
        personalization=personalization,
        email_status='',
        linkedin_status='',
        reply_status=''
    )
    db.session.add(contact)
    db.session.commit()
    
    return jsonify({'success': True, 'id': contact.id})

@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    data = request.json
    if 'email_status' in data:
        contact.email_status = data['email_status']
    if 'linkedin_status' in data:
        contact.linkedin_status = data['linkedin_status']
    if 'reply_status' in data:
        contact.reply_status = data['reply_status']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/stats')
def get_stats():
    total_museums = Museum.query.count()
    total_contacts = Contact.query.count()
    contacts_with_email = Contact.query.filter(Contact.email != '', Contact.email != None).count()
    emails_sent = Contact.query.filter(Contact.email_status == 'Sent').count()
    positive_replies = Contact.query.filter(Contact.reply_status == 'Positive Reply').count()
    interested_museums = Museum.query.filter(Museum.interest == 'Yes').count()
    
    return jsonify({
        'total_museums': total_museums,
        'total_contacts': total_contacts,
        'contacts_with_email': contacts_with_email,
        'emails_sent': emails_sent,
        'positive_replies': positive_replies,
        'interested_museums': interested_museums
    })

@app.route('/api/import', methods=['POST'])
def import_data():
    data = request.json
    
    museums_added = 0
    contacts_added = 0
    
    for m in data.get('museums', []):
        name = m.get('name', '').strip()
        if not name:
            continue
        existing = Museum.query.filter_by(name=name).first()
        if existing:
            continue
        museum = Museum(
            name=name,
            website=m.get('website', ''),
            address=m.get('address', ''),
            personalization=m.get('personalization', ''),
            interest=''
        )
        db.session.add(museum)
        museums_added += 1
    
    db.session.commit()
    
    for c in data.get('contacts', []):
        name = c.get('name', '').strip()
        if not name:
            continue
        museum_name = c.get('museum', '').strip()
        existing = Contact.query.filter_by(name=name, museum=museum_name).first()
        if existing:
            continue
        
        museum = Museum.query.filter_by(name=museum_name).first()
        
        contact = Contact(
            name=name,
            first_name=extract_first_name(name),
            title=c.get('title', ''),
            museum=museum_name,
            museum_id=museum.id if museum else None,
            email=extract_email(c.get('email', '')),
            linkedin=c.get('linkedin', ''),
            personalization=c.get('personalization', ''),
            email_status='',
            linkedin_status='',
            reply_status=''
        )
        db.session.add(contact)
        contacts_added += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'museums_added': museums_added,
        'contacts_added': contacts_added,
        'total_museums': Museum.query.count(),
        'total_contacts': Contact.query.count()
    })

@app.route('/import')
def import_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Import Data</title>
        <style>
            body { font-family: 'Poppins', sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #FDF8F5; }
            textarea { width: 100%; height: 300px; margin: 10px 0; border: 2px solid #f0e6e0; border-radius: 12px; padding: 15px; font-family: monospace; }
            button { background: linear-gradient(135deg, #E0B0FF 0%, #C9A0FF 100%); border: none; padding: 12px 25px; cursor: pointer; font-size: 16px; border-radius: 25px; font-weight: 600; }
            button:hover { transform: translateY(-1px); }
            #result { margin-top: 20px; padding: 15px; background: #FFF5F0; display: none; border-radius: 12px; }
        </style>
    </head>
    <body>
        <h1>Import Data</h1>
        <p>Paste the JSON data below:</p>
        <textarea id="data" placeholder='{"museums": [...], "contacts": [...]}'></textarea>
        <button onclick="importData()">Import</button>
        <div id="result"></div>
        <script>
            async function importData() {
                const data = document.getElementById('data').value;
                try {
                    const parsed = JSON.parse(data);
                    const res = await fetch('/api/import', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(parsed)
                    });
                    const result = await res.json();
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('result').innerHTML = `
                        <strong>Import Complete!</strong><br>
                        Museums added: ${result.museums_added}<br>
                        Contacts added: ${result.contacts_added}<br>
                        Total museums: ${result.total_museums}<br>
                        Total contacts: ${result.total_contacts}
                    `;
                } catch (e) {
                    alert('Error: ' + e.message);
                }
            }
        </script>
    </body>
    </html>
    '''

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
