#!/usr/bin/env python3
"""
Import CSV data into the Kensho CRM database.
Run this after deploying to Railway with DATABASE_URL set.
"""

import os
import csv
import re
from app import app, db, Museum, Contact

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

def import_museums(csv_path):
    print(f"Importing museums from {csv_path}")
    count = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Name', '').strip()
            if not name:
                continue
            
            # Check if exists
            existing = Museum.query.filter_by(name=name).first()
            if existing:
                continue
                
            museum = Museum(
                name=name,
                website=row.get('Website', ''),
                address=row.get('Address', ''),
                personalization=row.get('Personalization Fields specific Project Or Value', ''),
                interest=''
            )
            db.session.add(museum)
            count += 1
    
    db.session.commit()
    print(f"  Imported {count} museums")

def import_contacts(csv_path):
    print(f"Importing contacts from {csv_path}")
    count = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Name', '').strip()
            if not name:
                continue
            
            # Check if exists
            existing = Contact.query.filter_by(name=name, museum=row.get('Musuem Name', '')).first()
            if existing:
                continue
            
            museum_name = row.get('Musuem Name', '').strip()
            museum = Museum.query.filter_by(name=museum_name).first()
            
            contact = Contact(
                name=name,
                first_name=extract_first_name(name),
                title=row.get('Title', ''),
                museum=museum_name,
                museum_id=museum.id if museum else None,
                email=extract_email(row.get('Find Work Email', '')),
                linkedin=row.get('Url', ''),
                personalization=row.get('Personalization Fields specific Project Or Value', ''),
                email_status='',
                linkedin_status='',
                reply_status=''
            )
            db.session.add(contact)
            count += 1
    
    db.session.commit()
    print(f"  Imported {count} contacts")

if __name__ == '__main__':
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Import data - adjust paths as needed
        museums_csv = os.environ.get('MUSEUMS_CSV', 'data/museums.csv')
        contacts_csv = os.environ.get('CONTACTS_CSV', 'data/contacts.csv')
        
        if os.path.exists(museums_csv):
            import_museums(museums_csv)
        else:
            print(f"Museums CSV not found: {museums_csv}")
            
        if os.path.exists(contacts_csv):
            import_contacts(contacts_csv)
        else:
            print(f"Contacts CSV not found: {contacts_csv}")
        
        print("\nDone!")
        print(f"  Museums: {Museum.query.count()}")
        print(f"  Contacts: {Contact.query.count()}")
