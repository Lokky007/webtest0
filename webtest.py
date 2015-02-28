#!/usr/bin/env python
# -*- coding: utf8 -*-
# Soubor:  webtest.py
# Datum:   22.02.2015 16:35
# Autor:   Marek Nožka, marek <@t> tlapicka <d.t> net
# Licence: GNU/GPL
# Úloha:   Hlavní soubor aplikace WebTest
from __future__ import division, print_function, unicode_literals
############################################################################

from flask import (Flask, render_template,
                   # Markup,
                   request, url_for, redirect, session, )
from werkzeug.routing import BaseConverter
# from typogrify.filters import typogrify
# from markdown import markdown
from pony.orm import (sql_debug, get, select, db_session)
# from datetime import datetime
import os
import functools
from crypt import crypt
from wtdb import Student, Ucitel, Otazka

import sys
reload(sys)  # to enable `setdefaultencoding` again
sys.setdefaultencoding("UTF-8")
app = Flask('WebTest')
app.secret_key = os.urandom(24)


############################################################################
class RegexConverter(BaseConverter):
    "Díky této funci je možné do routovat pomocí regulárních výrazů"
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

app.url_map.converters['regex'] = RegexConverter


def prihlasit(klic):
    """Dekoruje funkce, které vyžadují přihlášení

    @prihlasit(klic)
    klic: je klic ve slovniku session, který se kontroluje.
    """
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if klic in session:
                return function(*args, **kwargs)
            else:
                return redirect(url_for('login', url=request.path))
        return wrapper
    return decorator


def pswd_check(pswd, encript):
    """Kontroluje heslo a hash hesla v DB.

    pswd: heslo od uživatele
    encript: šífrované heslo uložené v DB
    """
    i = encript.rfind('$')
    salt = encript[:i]
    return encript == crypt(pswd, salt)


############################################################################


@app.route('/')
def index():
    if 'student' in session:
        return render_template('student.html')
    elif 'ucitel' in session:
        return render_template('ucitel.html')
    else:
        return redirect(url_for('login'))


@app.route('/login/', methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        with db_session:
            if 'student' in session:
                student = get(s for s in Student
                              if s.login == session[b'student'])
                return render_template('login.html', jmeno=student.jmeno)
            elif 'ucitel' in session:
                ucitel = get(u for u in Ucitel
                             if u.login == session[b'ucitel'])
                return render_template('login.html', jmeno=ucitel.jmeno)
        if 'url' in request.args:
            return render_template('login.html', url=request.args['url'])
        else:
            return render_template('login.html')
    elif request.method == 'POST':
        login = request.form['login']
        heslo = request.form['passwd']
        with db_session:
            student_hash = get(s.hash for s in Student if s.login == login)
            ucitel_hash = get(u.hash for u in Ucitel if u.login == login)
        if student_hash and pswd_check(heslo, student_hash):
            session['student'] = login
            if 'url' in request.form:
                return redirect(request.form['url'])
            else:
                return redirect(url_for('index'))
        elif ucitel_hash and pswd_check(heslo, ucitel_hash):
            session['ucitel'] = login
            if 'url' in request.form:
                return redirect(request.form['url'])
            else:
                return redirect(url_for('index'))
        else:  # špatně
            if 'url' in request.form:
                return render_template('login.html', spatne=True,
                                       url=request.form['url'])
            else:
                return render_template('login.html', spatne=True)


@app.route('/logout/', methods=['GET'])
def logout():
    if 'student' in session:
        session.pop('student', None)
    elif 'ucitel' in session:
        session.pop('ucitel', None)
    return redirect(url_for('login'))


@app.route('/vysledky/', methods=['GET', 'POST'])
@prihlasit('ucitel')
def vysledky():
    if request.method == 'GET':
        return render_template('vysledky.html')
    elif request.method == 'POST':
        return redirect(url_for('/'))


@app.route('/otazky/', methods=['GET', 'POST'])
@prihlasit('ucitel')
@db_session
def otazky():
    #: Zobrazí všechny otázky a nabídne příslušné akce
    if request.method == 'GET':
        otazky = select((o.id, o.ucitel.login, o.ucitel.jmeno, o.jmeno,
                        o.obecne_zadani) for o in Otazka)
        return render_template('otazky.html', otazky=otazky)
    elif request.method == 'POST':
        return redirect(url_for('/'))


@app.route('/testy/', methods=['GET', 'POST'])
@prihlasit('ucitel')
def testy():
    if request.method == 'GET':
        return render_template('testy.html')
    elif request.method == 'POST':
        return redirect(url_for('/'))


@app.route('/pridat/otazku/', methods=['GET', 'POST'])
@prihlasit('ucitel')
def pridat_otazku():
    r = request
    r.f = r.form
    if r.method == 'GET':
        if 'ok' in r.args:
            zprava = 'Proběhlo vložení otázky "' + r.args['ok'] + '".'
            return render_template('pridat_otazku.html', vlozeno=zprava)
        else:
            return render_template('pridat_otazku.html')
    elif r.method == 'POST':
        if r.f['jmeno'] and r.f['typ_otazky'] and r.f['obecne_zadani']:
            if r.f['typ_otazky'] == 'O':
                with db_session:
                    Otazka(ucitel=get(u for u in Ucitel
                                      if u.login == session['ucitel']),
                           jmeno=r.f['jmeno'],
                           typ_otazky='O',
                           obecne_zadani=r.f['obecne_zadani'])
                return redirect(url_for('pridat_otazku', ok=r.f['jmeno']))
            elif r.f['typ_otazky'] == 'C' and r.f['spravna_odpoved']:
                with db_session:
                    Otazka(ucitel=get(u for u in Ucitel
                                      if u.login == session['ucitel']),
                           jmeno=r.f['jmeno'],
                           typ_otazky='C',
                           obecne_zadani=r.f['obecne_zadani'],
                           spravna_odpoved=r.f['spravna_odpoved'])
                return redirect(url_for('pridat_otazku', ok=r.f['jmeno']))
            elif r.f['typ_otazky'] == 'U' and r.f['spravna_odpoved']:
                # Musím dát všechny špatné odpovědi těsně za sebe
                KLICE = ('spatna_odpoved1', 'spatna_odpoved2',
                         'spatna_odpoved3', 'spatna_odpoved4',
                         'spatna_odpoved5', 'spatna_odpoved6')
                odpovedi = []
                for klic in KLICE:
                    if r.f[klic]:
                        odpovedi.append(r.f[klic])
                parametry = {}
                i = 0
                for odpoved in odpovedi:
                    parametry[KLICE[i]] = odpoved
                    i += 1
                # Chce to alespoň jednu špatnou odpověď
                if len(parametry) < 1:
                    zprava = "... alespoň jednu špatnou odpověď!"
                    return render_template('pridat_otazku.html', chyba=zprava)
                with db_session:
                    Otazka(ucitel=get(u for u in Ucitel
                                      if u.login == session['ucitel']),
                           jmeno=r.f['jmeno'],
                           typ_otazky='U',
                           obecne_zadani=r.f['obecne_zadani'],
                           spravna_odpoved=r.f['spravna_odpoved'],
                           **parametry)
                return redirect(url_for('pridat_otazku', ok=r.f['jmeno']))
            else:
                zprava = "U číselné otázky musí být zadán správná odpověď."\
                         " U uzavrené otázky i špatná odpověď."
                return render_template('pridat_otazku.html', chyba=zprava)
        else:
            zprava = "Nebyla zadána všechna požadovaná data."
            return render_template('pridat_otazku.html', chyba=zprava)


@app.route('/pridat/test/', methods=['GET', 'POST'])
@prihlasit('ucitel')
def pridat_test():
    if request.method == 'GET':
        return render_template('pridat_test.html')
    elif request.method == 'POST':
        return redirect(url_for('upload'))


@app.route('/upload/', methods=['GET', 'POST'])
@prihlasit('ucitel')
@db_session
def upload():
    def add(typ, nazev_otazky, cislo, otazka, spravna, spatna):  # zapis do db 
        ucitel = get(u for u in Ucitel if u.login == session['ucitel'])
        while len(spatna)<7:  # doplni hodnoty NULL do nevyuzitych mist
            spatna.append('Null')

        spatna = [unicode(i) for i in spatna]   # prevede polozky seznamu na UNICODE
        Otazka(ucitel=ucitel, jmeno=nazev_otazky, typ_otazky=typ, obecne_zadani='10',
                spravna_odpoved=spravna, spatna_odpoved1=spatna[0], 
                spatna_odpoved2=spatna[1], spatna_odpoved3=spatna[2],
                spatna_odpoved4=spatna[3], spatna_odpoved5=spatna[4],
                spatna_odpoved6=spatna[5]) # Obecne_zadani nastaveno perma na 10
        
    if request.method == 'GET':
        return render_template('upload.html')
    elif request.method == 'POST':
        if 'datafile' in request.files:
            fil = request.files['datafile']
            typ = cislo = nazev_otazky =  otazka = spravna = ""
            spatna = []  # seznam spatnych odpovedi
            for line in fil:
                radek = line.strip().decode('UTF-8') 
                
                if line != '\n':  # ignoruj prazdne radky
                    if radek.split()[0] == '::date':
                        datum = " ".join(radek.split()[1:])
                    elif radek.split()[0] == '::number':
                        typ = 'Hodnota' 
                        spravna = " ".join(radek.split()[1:])                    
                    elif radek.split()[0] == ':+':
                        spravna = " ".join(radek.split()[1:])
                    elif radek.split()[0] == ':-':
                        spatna.append(radek.split()[1:])
                    elif radek.split()[0] == '::task':
                        nazev_otazky = " ".join(radek.split()[1:])
                    elif radek.split()[0] == '::open':
                        typ = 'Otevrena'
                    elif radek.split()[0] == '::close':
                        typ = 'Uzavrena'
                    else:
                        otazka = otazka + line
                else:  # kdyz je mezera(oddeleni otazek), udelej zapis do DB
                    if nazev_otazky and otazka:  #ignoruj 1.mezeru(a nekor. otazky) 
                        add(typ, nazev_otazky,cislo, otazka, spravna, spatna)
                    typ = nazev_otazky = cislo = otazka = spravna = "" # vynuluj
                    spatna = []
                                       
        return redirect(url_for('upload'))

##########  Datum v zadani nebude?
##########  Rozsah nahodneho čislo ??
########## typ_otazky v DB je nastaven na 1 znak ??? (Docasne nastaveno na 80)

############################################################################


if __name__ == '__main__':
    sql_debug(True)
    app.run(host='127.0.0.1', port=8080, debug=True)
