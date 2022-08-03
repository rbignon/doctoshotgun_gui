"""
Book vaccine slots on Doctolib
"""
import asyncio
import concurrent.futures
import os
import json
import webbrowser
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from woob.exceptions import ScrapingBlocked, BrowserInteraction
from doctoshotgun.doctolib import DoctolibFR, DoctolibDE, Appointment

def disable_button(button):
    button.enabled = False
    button.style.background_color = '#aaaaaa'

def enable_button(button):
    button.enabled = True
    button.style.background_color = '#383D76'


class Doctoshotgun(toga.App):
    countries = {'France': DoctolibFR,
                 'Germany': DoctolibDE,
                }

    STATE_FILENAME = 'state.json'

    docto = None
    patient_input = None
    custom_fields = None

    def load_state(self):
        print('===== LOAD FROM', self.paths.data)
        try:
            with open(self.paths.data / self.STATE_FILENAME, 'r') as fp:
                state = json.load(fp)
                print(state)
        except IOError:
            return {}
        else:
            return state

    def save_state(self, state):
        print('==== DUMP TO', self.paths.data / self.STATE_FILENAME)
        if not os.path.exists(self.paths.data):
            os.makedirs(self.paths.data)
        with open(self.paths.data / self.STATE_FILENAME, 'w') as fp:
            json.dump(state, fp)

    def exit_handler(self, app):
        if self.docto:
            self.save_state(self.docto.dump_state())
        return True

    def startup(self):
        """
        Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """

        self.on_exit = self.exit_handler

        intro1 = toga.Label('When and where', style=Pack(font_weight='bold', font_size=16, color='#383D76'))
        intro2 = toga.Label('would you like to book a vaccine slot?', style=Pack(font_size=14, color='#383D76'))
        intro_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50),
                             children=[intro1, intro2])

        self.country_label = toga.Label('Country', style=Pack(color='#383D76'))
        self.country_input = toga.Selection(items=list(self.countries.keys()),
                                            style=Pack(padding_top=10, color='#383D76'))
        country_box = toga.Box(style=Pack(direction=COLUMN, padding=20, color='#383D76'),
                               children=[self.country_label, self.country_input])

        self.zip_label = toga.Label('ZIP code', style=Pack(color='#383D76'))
        self.zip_input = toga.TextInput(style=Pack(color='#383D76'))
        zip_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                             children=[self.zip_label, self.zip_input])

        self.start_date_label = toga.Label('From', style=Pack(color='#383D76'))
        self.start_date_input = toga.TextInput(style=Pack(flex=1, color='#383D76'),
                                               initial=date.today().strftime('%d/%m/%Y'))
        start_date_box = toga.Box(style=Pack(direction=COLUMN, padding_right=10, flex=1),
                             children=[self.start_date_label, self.start_date_input])

        self.end_date_label = toga.Label('To', style=Pack(color='#383D76'))
        self.end_date_input = toga.TextInput(style=Pack(flex=1, color='#383D76'),
                                             initial=(date.today() + relativedelta(days=30)).strftime('%d/%m/%Y'))
        end_date_box = toga.Box(style=Pack(direction=COLUMN, padding_left=10, flex=1),
                             children=[self.end_date_label, self.end_date_input])

        date_box = toga.Box(style=Pack(direction=ROW, padding=20),
                            children=[start_date_box,
                                      end_date_box])

        validate_button = toga.Button('Continue',
                                      style=Pack(padding=20, background_color='#383D76', color='#ffffff'),
                                      on_press=self.go_to_login)

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                            children=[intro_box,
                                      country_box,
                                      zip_box,
                                      date_box,
                                      validate_button])

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

        #a = Appointment()
        #a.slots = [datetime.now()]
        #self.confirm_center(a)

    async def go_to_login(self, widget):
        self.country = self.country_input.value
        self.start_date = datetime.strptime(self.start_date_input.value, '%d/%m/%Y').date()
        self.end_date = datetime.strptime(self.end_date_input.value, '%d/%m/%Y').date()
        self.zip = self.zip_input.value

        validate_button = toga.Button('Continue',
                                      style=Pack(padding=20, background_color='#383D76', color='#ffffff'),
                                      on_press=self.login)

        def input_changed(widget):
            if self.login_input.value and self.password_input.value:
                enable_button(validate_button)
            else:
                disable_button(validate_button)

        intro1 = toga.Label('Your Doctolib login is needed', style=Pack(font_weight='bold', font_size=16, color='#383D76'))
        intro2 = toga.Label('to find a vaccination slot', style=Pack(font_size=14, color='#383D76'))
        intro_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50),
                             children=[intro1, intro2])

        self.login_label = toga.Label('Email address', style=Pack(color='#383D76'))
        self.login_input = toga.TextInput(placeholder='example@gmail.com', initial='',
                                          style=Pack(color='#383D76'),
                                          on_change=input_changed)
        login_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                             children=[self.login_label, self.login_input])

        self.password_label = toga.Label('Password', style=Pack(color='#383D76'))
        self.password_input = toga.PasswordInput(style=Pack(color='#383D76'), initial='',
                                                 on_change=input_changed)
        password_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                                           children=[self.password_label, self.password_input])

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                            children=[intro_box,
                                      login_box,
                                      password_box,
                                      validate_button])

        self.main_window.content = main_box
        self.main_window.show()

        self.login_input.focus()

    def login(self, widget):
        disable_button(widget)

        klass = self.countries[self.country]
        self.docto = klass(self.login_input.value, self.password_input.value)
        self.docto.load_state(self.load_state())
        try:
            if not self.docto.do_login():
                enable_button(widget)
                self.login_label.style.color = '#ff0000'
                self.login_input.style.color = '#ff0000'
                self.password_label.style.color = '#ff0000'
                self.password_input.style.color = '#ff0000'
                return
        except ScrapingBlocked as e:
            self.main_window.info_dialog('Oops', str(e))
            enable_button(widget)
            return
        except BrowserInteraction as e:
            return self.go_to_otp()

        self.go_to_vaccine()

    def go_to_otp(self):
        intro1 = toga.Label('Enter the code received', style=Pack(font_weight='bold', font_size=16, color='#383D76'))
        intro2 = toga.Label('at your email address from Doctolib', style=Pack(font_size=14, color='#383D76'))
        intro_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50),
                             children=[intro1, intro2])

        validate_button = toga.Button('Continue',
                                      style=Pack(padding=20, background_color='#383D76', color='#ffffff'),
                                      on_press=self.send_otp)

        def code_changed(widget, next_input=None):
            if widget.value != '':
                if len(widget.value) > 1:
                    widget.value = widget.value[0]
                if not widget.value.isdigit():
                    widget.value = ''
                elif next_input:
                    getattr(self, 'code%s_input' % next_input).focus()

            for x in range(6):
                if not getattr(self, 'code%s_input' % (x+1)).value:
                    disable_button(validate_button)
                    return

            enable_button(validate_button)

        self.code_label = toga.Label('Code', style=Pack(color='#383D76'))
        self.code1_input = toga.TextInput(style=Pack(font_weight='bold', font_size=28, color='#383D76'), on_change=lambda w: code_changed(w, '2'))
        self.code2_input = toga.TextInput(style=Pack(font_weight='bold', font_size=28, color='#383D76'), on_change=lambda w: code_changed(w, '3'))
        self.code3_input = toga.TextInput(style=Pack(font_weight='bold', font_size=28, color='#383D76'), on_change=lambda w: code_changed(w, '4'))
        self.code4_input = toga.TextInput(style=Pack(font_weight='bold', font_size=28, color='#383D76'), on_change=lambda w: code_changed(w, '5'))
        self.code5_input = toga.TextInput(style=Pack(font_weight='bold', font_size=28, color='#383D76'), on_change=lambda w: code_changed(w, '6'))
        self.code6_input = toga.TextInput(style=Pack(font_weight='bold', font_size=28, color='#383D76'), on_change=lambda w: code_changed(w))
        code_input_box = toga.Box(style=Pack(direction=ROW),
                                  children=[self.code1_input,
                                            self.code2_input,
                                            self.code3_input,
                                            self.code4_input,
                                            self.code5_input,
                                            self.code6_input])
        code_box = toga.Box(style=Pack(direction=COLUMN, padding=30),
                            children=[self.code_label, code_input_box])

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                            children=[intro_box,
                                      code_box,
                                      validate_button])

        self.main_window.content = main_box
        self.main_window.show()

        self.code1_input.focus()

    def send_otp(self, widget):
        disable_button(widget)

        code = ''
        for x in range(6):
            code += getattr(self, 'code%s_input' % (x+1)).value

        if not self.docto.do_otp(code):
            self.main_window.info_dialog('Oops', 'Invalid auth code')
            enable_button(widget)
            return

        # Save storage to prevent doing OTP next time.
        self.save_state(self.docto.dump_state())

        self.go_to_vaccine()

    def go_to_vaccine(self):
        self.patients = {'%(first_name)s %(last_name)s' % patient: patient for patient in self.docto.get_patients()}
        if len(self.patients) > 0:
            self.patient_label = toga.Label('Patient', style=Pack(color='#383D76'))
            self.patient_input = toga.Selection(items=list(self.patients.keys()),
                                                style=Pack(padding_top=10, color='#383D76'))
            patient_box = toga.Box(style=Pack(direction=COLUMN, padding=20, color='#383D76'),
                                   children=[self.patient_label, self.patient_input])
        else:
            self.patient_input = None
            patient_box = None
            self.docto.patient = list(self.patients.values())[0]

        validate_button = toga.Button('Continue',
                                      style=Pack(padding=20, background_color='#383D76', color='#ffffff'),
                                      on_press=self.find_centers)

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                            children=[validate_button])
        if patient_box:
            main_box.children.insert(0, patient_box)

        self.main_window.content = main_box
        self.main_window.show()

    async def find_centers(self, button=None):
        if self.patient_input and self.patient_input.value:
            self.docto.patient = self.patients[self.patient_input.value]

        intro1 = toga.Label('Alright!', style=Pack(font_weight='bold', font_size=16, color='#383D76'))
        intro2 = toga.Label('the app is searching for a slot!', style=Pack(font_size=14, color='#383D76'))
        intro_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50),
                             children=[intro1, intro2])

        body1 = toga.Label('How long this could take?', style=Pack(font_weight='bold', font_size=12, color='#383D76', flex=1))
        body2 = toga.Label('It could take a while, from few seconds to few hours. Please do not close the app during this time.', style=Pack(font_size=10, color='#383D76', flex=1))
        body_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50, padding_right=20, flex=1),
                             children=[body1, body2])

        image = toga.ImageView(toga.Image('resources/loading.png'), style=Pack(alignment='center', flex=1))
        image_box = toga.Box(style=Pack(padding_left=20, padding_right=20, flex=1, alignment='center'),
                             children=[image])

        progress_title = toga.Label('Searching…', style=Pack(font_weight='bold', font_size=12, color='#383D76', flex=1, alignment='center'))
        self.progress_line0 = toga.Label('', style=Pack(font_size=12, color='#ff0000', flex=1))
        self.progress_line1 = toga.Label('', style=Pack(font_size=12, color='#ff0000', flex=1))
        self.progress_line2 = toga.Label('', style=Pack(font_size=12, color='#ff0000', flex=1))
        self.progress_line3 = toga.Label('', style=Pack(font_size=12, color='#383D76', flex=1))
        progress_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50),
                             children=[progress_title,
                                       self.progress_line0,
                                       self.progress_line1,
                                       self.progress_line2,
                                       self.progress_line3])


        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                            children=[intro_box,
                                      body_box,
                                      image_box,
                                      progress_box])

        self.main_window.content = main_box
        self.main_window.show()

        def set_status(text):
            for x in range(3):
                getattr(self, 'progress_line%s' % x).text = getattr(self, 'progress_line%s' % (x+1)).text
            self.progress_line3.text = text

        def append_status(text):
            self.progress_line3.text += text


        motives = [self.docto.KEY_PFIZER_THIRD, self.docto.KEY_MODERNA_THIRD]
        vaccine_list = [self.docto.vaccine_motives[motive] for motive in motives]
        cities = ['paris']

        while True:
            for center in self.docto.find_centers(cities, motives):
                set_status('Center %(name_with_title)s (%(city)s)... ' % center)
                await asyncio.sleep(0.1)

                for appointment in self.docto.find_appointments(center, vaccine_list, self.start_date, self.end_date, [], False, True):
                    await asyncio.sleep(0.1)
                    self.progress_line3.style.color = '#00ff00'
                    append_status('found!')
                    return self.confirm_center(appointment)
                else:
                    append_status('not found')

                await asyncio.sleep(1)

            await asyncio.sleep(5)

    def confirm_center(self, appointment):
        intro = toga.Label('A slot has been found!', style=Pack(font_weight='bold', font_size=16, color='#383D76'))
        intro_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50),
                             children=[intro])

        vaccine = toga.Label('%s vaccine' % appointment.vaccine.replace('.*', ' '), style=Pack(font_weight='bold', color='#383D76'))
        patient = toga.Label('for %(first_name)s %(last_name)s' % self.docto.patient, style=Pack(color='#383D76'))
        #patient = toga.Label('for %(first_name)s %(last_name)s', style=Pack(color='#383D76'))
        vaccine_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_right=20, background_color='#EFF6FE'),
                               children=[vaccine, patient])


        slots_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_right=20))
        for slot in appointment.slots:
            date = toga.Label(slot.strftime('%d/%m/%Y'), style=Pack(color='#383D76'))
            date_box = toga.Box(style=Pack(direction=ROW, padding_right=20, background_color='#FCF4EF'),
                                children=[date])
            time = toga.Label(slot.strftime('%H:%M'), style=Pack(color='#383D76'))
            time_box = toga.Box(style=Pack(direction=ROW, padding_left=20, background_color='#FCF4EF'),
                                children=[time])
            slot_box = toga.Box(style=Pack(direction=ROW), children=[date_box, time_box])
            slots_box.children.append(slot_box)

        map_view = toga.WebView(style=Pack(flex=1))
        map_view.set_content(None, f"""<html>
<body style="margin:0px;padding:0px;overflow:hidden">
    <iframe src="{appointment.map_url}" frameborder="0" style="overflow:hidden;height:100%;width:100%" height="100%" width="100%">
    </iframe>
</body>
</html>""")
        map_box = toga.Box(style=Pack(padding_left=20, padding_right=20, flex=1, height=200),
                           children=[map_view])

        center_name = toga.Label(appointment.name, style=Pack(color='#383D76'))
        address1 = toga.Label(appointment.address, style=Pack(color='#383D76'))
        address2 = toga.Label(f'{appointment.zipcode} {appointment.city}', style=Pack(color='#383D76'))
        address_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_right=20, padding_top=20),
                               children=[center_name, address1, address2])

        self.custom_fields = {}
        fields_box = toga.Box(style=Pack(padding_left=20, padding_top=20))

        for field in appointment.custom_fields:
            if field['id'] == 'cov19':
                value = 'Non'
            elif field['placeholder']:
                value = field['placeholder']
            else:
                label = toga.Label(field['label'], style=Pack(padding_top=20, color='#383D76'))
                if field.get('options'):
                    value = toga.Selection(items=field['options'], style=Pack(padding_top=10, color='#383D76'))
                else:
                    value = toga.TextInput(placeholder=field['placeholder'], style=Pack(color='#383D76'))
                fields_box.children.append(label)
                fields_box.children.append(value)

            self.custom_fields[field['id']] = value


        validate_button = toga.Button('Book it now',
                                      style=Pack(padding=20, background_color='#383D76', color='#ffffff'),
                                      on_press=lambda _: self.book_appointment(appointment))

        cancel_button = toga.Button('Search again',
                                      style=Pack(padding=20, background_color='#ffffff', color='#9B9EBA'),
                                      on_press=self.find_centers)

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                            children=[intro_box,
                                      vaccine_box,
                                      slots_box,
                                      map_box,
                                      address_box,
                                      fields_box,
                                      validate_button,
                                      cancel_button])

        self.main_window.content = main_box
        self.main_window.show()

    def book_appointment(self, appointment):
        custom_fields = {}
        for key, value in self.custom_fields.items():
            if isinstance(value, toga.Widget):
                custom_fields[key] = value.value
            else:
                custom_fields[key] = value

        r = self.docto.book_appointment(appointment, custom_fields)

        if not r:
            self.main_window.info_dialog('Oops', 'Unable to book your slot')
            return

        intro = toga.Label('Your slot is booked!', style=Pack(font_weight='bold', font_size=16, color='#383D76'))
        intro_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_bottom=50),
                             children=[intro])

        vaccine = toga.Label('%s vaccine' % appointment.vaccine.replace('.*', ' ').title(), style=Pack(font_weight='bold', color='#383D76'))
        patient = toga.Label('for %(first_name)s %(last_name)s' % self.docto.patient, style=Pack(color='#383D76'))
        vaccine_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_top=70, padding_right=20, background_color='#EFF6FE'),
                               children=[vaccine, patient])

        slots_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_right=20))
        for slot in appointment.slots:
            date = toga.Label(slot.strftime('%d/%m/%Y'), style=Pack(color='#383D76'))
            date_box = toga.Box(style=Pack(direction=ROW, padding_right=20, background_color='#FCF4EF'),
                                children=[date])
            time = toga.Label(slot.strftime('%H:%M'), style=Pack(color='#383D76'))
            time_box = toga.Box(style=Pack(direction=ROW, padding_left=20, background_color='#FCF4EF'),
                                children=[time])
            slot_box = toga.Box(style=Pack(direction=ROW), children=[date_box, time_box])
            slots_box.children.append(slot_box)

        center_name = toga.Label(appointment.name, style=Pack(color='#383D76'))
        address1 = toga.Label(appointment.address, style=Pack(color='#383D76'))
        address2 = toga.Label(f'{appointment.zipcode} {appointment.city}', style=Pack(color='#383D76'))
        address_box = toga.Box(style=Pack(direction=COLUMN, padding_left=20, padding_right=20, padding_top=20),
                               children=[center_name, address1, address2])

        validate_button = toga.Button('Open Doctolib',
                                      style=Pack(padding=20, background_color='#383D76', color='#ffffff'),
                                      on_press=lambda _: webbrowser.open(self.docto.BASEURL))

        close_button = toga.Button('Close app',
                                   style=Pack(padding=20, background_color='#ffffff', color='#9B9EBA'),
                                   on_press=lambda _: self.exit())

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20),
                            children=[intro_box,
                                      vaccine_box,
                                      slots_box,
                                      address_box,
                                      validate_button,
                                      close_button])

        self.main_window.content = main_box
        self.main_window.show()


        #print('go go go')
        #import janus
        #import threading

        #loop = self._impl.loop
        ##loop = asyncio.get_event_loop()

        ##queue = janus.Queue()
        #queue = asyncio.Queue()
        #threading.Thread(target=self.do_things, args=(queue,)).start()

        ##with concurrent.futures.ThreadPoolExecutor() as pool:
        ##    queue = asyncio.Queue()

        ##    task = loop.run_in_executor(pool, self.do_things, queue.sync_q)
        #while True:
        #    print('wait for event')
        #    event = await queue.get()

        #    print('got an event')
        #    if isinstance(event, NewEvent):
        #        for x in range(3):
        #            getattr(self, 'progress_line%s' % x).text = getattr(self, 'progress_line%s' % (x+1)).text
        #        self.progress_line3.text = event.text
        #    elif isinstance(event, UpdateEvent):
        #        self.progress_line3.text += event.text
        #    elif isinstance(event, FoundEvent):
        #        break


    def do_things(self, queue):
        print('do things')
        try:
            from time import sleep
            import requests
            for x in range(5):
                print('first sleep')
                requests.get('https://www.google.com')
                print('send center')
                queue.put_nowait(NewEvent('Centre %s...' % x))
                sleep(2)
                print('send not found')
                queue.put_nowait(UpdateEvent(' not found'))
            queue.put_nowait(FoundEvent())
        finally:
            print('end')

class UpdateEvent:
    text: str

    def __init__(self, text):
        self.text = text

class NewEvent:
    text: str

    def __init__(self, text):
        self.text = text

class FoundEvent:
    text: str

def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    return Doctoshotgun()
