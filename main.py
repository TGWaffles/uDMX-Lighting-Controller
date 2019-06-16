import pyUDMX
import tkinter
import json
import os

from tkinter import ttk


class StorageHandler:
    def __init__(self):
        if not os.path.exists('storage.json'):
            self.storage_dict = {'presets': dict()}
            with open('storage.json', 'w') as storage_file:
                storage_file.write(json.dumps(self.storage_dict))
        else:
            self.read_storage()

    def write_storage(self):
        with open('storage.json', 'w') as storage_file:
            storage_file.write(json.dumps(self.storage_dict))

    def read_storage(self):
        with open('storage.json', 'r') as storage_file:
            self.storage_dict = json.loads(storage_file.read())

    def get_storage(self):
        self.read_storage()
        return self.storage_dict

    def read_variable(self, variable):
        self.read_storage()
        variable_value = self.storage_dict.get(variable, None)
        return variable_value

    def write_variable(self, variable, value):
        self.read_storage()
        self.storage_dict[variable] = value
        self.write_storage()

    def write_preset_dict(self, preset_dict):
        self.storage_dict['presets'] = preset_dict
        self.write_storage()

    def get_preset_dict(self):
        self.read_storage()
        return self.storage_dict['presets']


class USBInterface:
    def __init__(self):
        self.device = pyUDMX.uDMXDevice()
        self.device.open()

    def send_signal(self, channel, value):
        ...  # self.device.send_single_value(channel, value)

    def set_devices(self, **kwargs):
        channels = [int(channel) for channel in kwargs.keys()]
        with self.device as udmx:
            for channel in channels:
                value = kwargs.get(str(channel))
                udmx.send_single_value(channel, value)

    def reopen(self):
        self.device.close()
        self.device = pyUDMX.uDMXDevice()
        self.device.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.device.close()


class GUI:
    def __init__(self, interface, storage):
        self.storage = storage
        self.interface = interface
        self.master = tkinter.Tk()
        self.tabs = tkinter.ttk.Notebook(self.master)
        self.master.protocol("WM_DELETE_WINDOW", self.close_window)
        self.master.title("Lighting Desk")
        self.editor_frame = tkinter.Frame(self.tabs)
        self.tabs.add(self.editor_frame, text="Editor")
        self.preset_frame = tkinter.Frame(self.tabs)
        self.tabs.add(self.preset_frame, text="Presets")
        self.preset_name_list = []
        self.preset_list = []
        self.load_preset_dict(self.storage.get_preset_dict())
        self.preset_index = 0
        self.preset_entry = self.reset_button = self.blackout_button = self.preset_entry_text = None
        self.preset_box_length = 5
        self.preset_saver = self.preset_loader = self.clear_button = self.name_field = self.name_field_text = None
        self.slider_list = []
        self.manual_entry_list = []
        self.entry_list = []
        self.preset_slider_list = []
        self.blackout_value = self.blackout_value_previous = False
        self.slider_amount = 24
        self.grand_master = self.grand_master_manual_entry = None
        self.grand_master_manual_stringvar = tkinter.StringVar(value='255')
        self.grand_master_manual_stringvar.trace('w', self.limit_manual_entry_size)
        self.left_button = self.copy_button = self.paste_button = None
        self.create_editor_frame()
        self.last_slider_list_values = []
        self.count = 0
        self.update_preset_sliders()
        pad = 3
        self._geom = '200x200+0+0'
        self.master.geometry("{0}x{1}+0+0".format(
            self.master.winfo_screenwidth() - pad, self.master.winfo_screenheight() - pad))
        self.master.bind('<Escape>', self.shrink_window)
        self.tabs.pack()

    def shrink_window(self):
        geom = self.master.winfo_geometry()
        self.master.geometry(self._geom)
        self._geom = geom

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_preset_dict()

    def close_window(self):
        self.save_preset_dict()
        self.master.destroy()
        exit()

    def make_preset_dict(self):
        preset_dictionary = {}
        for i in range(len(self.preset_name_list)):
            if self.preset_name_list[i] is '':
                name = str(i)
            else:
                name = self.preset_name_list[i]
            preset_dictionary[name] = (i, self.preset_list[i])
        return preset_dictionary

    def save_preset_dict(self):
        preset_dict = self.make_preset_dict()
        self.storage.write_preset_dict(preset_dict)

    def load_preset_dict(self, preset_dictionary):
        name_list = [None] * len(preset_dictionary.keys())
        preset_list = [None] * len(preset_dictionary.keys())
        for name in preset_dictionary.keys():
            index = preset_dictionary[name][0]
            if name == str(index):
                name_list[index] = ''
            else:
                name_list[index] = name
            preset_list[index] = preset_dictionary[name][1]
        self.preset_name_list = name_list
        self.preset_list = preset_list

    def create_editor_frame(self):
        validate_command = (self.editor_frame.register(self.integer_verify),
                            '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        for i in range(self.slider_amount):
            self.manual_entry_list.append(tkinter.StringVar(value='0'))
            self.manual_entry_list[i].trace('w', self.limit_manual_entry_size)
            text_field = tkinter.Entry(self.editor_frame, validate='key', validatecommand=validate_command, width=3,
                                       textvariable=self.manual_entry_list[i])
            text_field.bind("<BackSpace>", self.backspace_handle)
            text_field.grid(row=0, column=i)
            self.entry_list.append(text_field)
            self.slider_list.append(tkinter.Scale(self.editor_frame, from_=255, to=0, width=20, length=200))
            self.slider_list[i].grid(row=1, column=i, ipadx=5)
            button = tkinter.Button(self.editor_frame, text=str(i+1))
            button.grid(row=2, column=i)
            button.bind('<ButtonPress-1>', lambda y,number=i+1: self.trigger_light(number, True))
            button.bind('<ButtonRelease-1>', lambda y,number=i+1: self.trigger_light(number, False))
        self.grand_master = tkinter.Scale(self.editor_frame, from_=255, to=0, width=25, length=200)
        self.grand_master.set(255)
        self.grand_master.grid(row=1, column=self.slider_amount+1, ipadx=10)
        self.blackout_button = tkinter.Label(self.editor_frame, text=str("BlackOut"))
        self.blackout_button.grid(row=2, column=self.slider_amount+1)
        self.blackout_button.bind('<ButtonPress-1>', lambda y: self.blackout())
        self.blackout_button.config(relief="raised")
        self.grand_master_manual_entry = tkinter.Entry(self.editor_frame, validate='key', validatecommand=validate_command,
                                                       width=3, textvariable=self.grand_master_manual_stringvar)
        self.grand_master_manual_entry.bind("<BackSpace>", self.backspace_handle)
        self.grand_master_manual_entry.grid(row=0, column=self.slider_amount+1)
        self.make_editor_preset_buttons(validate_command)

    def blackout(self):
        self.blackout_value = not self.blackout_value
        if self.blackout_value:
            self.blackout_button.config(relief="sunken")
        else:
            self.blackout_button.config(relief="raised")

    def trigger_light(self, number, toggle):
        if toggle:
            self.interface.send_signal(number, 255 * self.grand_master.get() // 255)
        else:
            value = self.slider_list[number-1].get() * self.grand_master.get() // 255
            self.interface.send_signal(number, value)

    def make_editor_preset_buttons(self, validate_command):
        self.left_button = tkinter.Button(self.editor_frame, text="<", command=self.button_left)
        self.left_button.grid(row=3, column=0)
        self.preset_entry_text = tkinter.StringVar(value='0')
        self.preset_entry_text.trace('w', self.limit_manual_entry_size)
        self.preset_entry = tkinter.Entry(self.editor_frame, validate='key', validatecommand=validate_command,
                                          width=self.preset_box_length, textvariable=self.preset_entry_text)
        self.preset_entry.grid(row=3, column=1)
        self.preset_entry.bind("<BackSpace>", self.backspace_handle)
        self.left_button = tkinter.Button(self.editor_frame, text=">", command=self.button_right)
        self.left_button.grid(row=3, column=2)
        self.preset_saver = tkinter.Button(self.editor_frame, text="Save", command=self.save_preset)
        self.preset_saver.grid(row=4, column=0)
        self.preset_saver = tkinter.Button(self.editor_frame, text="Load", command=self.load_preset)
        self.preset_saver.grid(row=4, column=1)
        self.clear_button = tkinter.Button(self.editor_frame, text="Clear", command=self.clear_preset)
        self.clear_button.grid(row=4, column=2)
        self.copy_button = tkinter.Button(self.editor_frame, text="Copy", command=self.clear_preset)
        self.copy_button.grid(row=3, column=6, columnspan=1, rowspan=2)
        self.paste_button = tkinter.Button(self.editor_frame, text="Paste", command=self.clear_preset)
        self.paste_button.grid(row=3, column=7, columnspan=1, rowspan=2)
        for i in range(self.slider_amount):

            self.preset_slider_list.append(tkinter.Scale(self.editor_frame, from_=255, to=0, width=20, length=100))
            self.preset_slider_list[i].config(state=tkinter.DISABLED)
            self.preset_slider_list[i].grid(row=5, column=i, ipadx=5, pady=10)
            label = tkinter.Label(self.editor_frame, text=str(i + 1))
            label.grid(row=6, column=i)
        self.name_field_text = tkinter.StringVar(value="")
        self.name_field = tkinter.Entry(self.editor_frame, width=25, textvariable=self.name_field_text)
        self.name_field.config(justify=tkinter.RIGHT)
        self.name_field.grid(row=3, column=3, columnspan=3, rowspan=2)
        self.reset_button = tkinter.Button(self.editor_frame, text="Fader Reset", command=self.fader_reset)
        self.reset_button.grid(row=3, column=8, columnspan=2, rowspan=2)
        try:
            if not any(self.preset_list[self.preset_index]):
                self.preset_entry.config({"background": "Red"})
            elif self.preset_list[self.preset_index]:
                self.preset_entry.config({"background": "Green"})
        except IndexError:
            self.preset_entry.config({"background": "Red"})

    def fader_reset(self):
        for i in range(len(self.slider_list)):
            slider = self.slider_list[i]
            self.manual_entry_list[i].set(0)
            slider.set(0)

    def update_preset_sliders(self):
        try:
            slider_list_values = self.preset_list[self.preset_index]
            self.name_field_text.set(self.preset_name_list[self.preset_index])
        except IndexError:
            slider_list_values = [0] * self.slider_amount
            self.name_field_text.set("")
        for i in range(len(slider_list_values)):
            self.preset_slider_list[i].config(state=tkinter.NORMAL)
            self.preset_slider_list[i].set(int(slider_list_values[i]))
            self.preset_slider_list[i].config(state=tkinter.DISABLED)

    def button_left(self):
        if self.preset_index == 0:
            if len(self.preset_list) > 1:
                self.preset_index = len(self.preset_list) - 1
            else: self.preset_index = 0
        else:
            self.preset_index -= 1
        if int(self.preset_entry_text.get()) != self.preset_index:
            self.preset_entry_text.set(self.preset_index)
        try:
            if not any(self.preset_list[self.preset_index]):
                self.preset_entry.config({"background": "Red"})
            elif self.preset_list[self.preset_index]:
                self.preset_entry.config({"background": "Green"})
        except IndexError:
            self.preset_entry.config({"background": "Red"})
        self.update_preset_sliders()

    def button_right(self):
        maximum_number = '9' * self.preset_box_length
        if self.preset_index + 1 > int(maximum_number):
            self.preset_index = 0
        else:
            self.preset_index += 1
        if int(self.preset_entry_text.get()) != self.preset_index:
            self.preset_entry_text.set(self.preset_index)
        try:
            if not any(self.preset_list[self.preset_index]):
                self.preset_entry.config({"background": "Red"})
            elif self.preset_list[self.preset_index]:
                self.preset_entry.config({"background": "Green"})
        except IndexError:
            self.preset_entry.config({"background": "Red"})
        self.update_preset_sliders()

    def save_preset(self):
        slider_list_values = [slider.get() for slider in self.slider_list]
        try:
            self.preset_list[self.preset_index] = slider_list_values
            self.preset_name_list[self.preset_index] = self.name_field_text.get()
        except IndexError:
            blank_slider_list = [0] * self.slider_amount
            for i in range(self.preset_index - len(self.preset_list) + 1):
                self.preset_list.append(blank_slider_list)
                self.preset_name_list.append("")
            self.preset_list[self.preset_index] = slider_list_values
            self.preset_name_list[self.preset_index] = self.name_field_text.get()
        try:
            if not any(self.preset_list[self.preset_index]):
                self.preset_entry.config({"background": "Red"})
            elif self.preset_list[self.preset_index]:
                self.preset_entry.config({"background": "Green"})
        except IndexError:
            self.preset_entry.config({"background": "Red"})
        self.update_preset_sliders()
        self.save_preset_dict()

    def clear_preset(self):
        try:
            self.preset_list[self.preset_index] = [0] * self.slider_amount
            self.preset_name_list[self.preset_index] = ''
            self.name_field_text.set("")
        except IndexError:
            pass
        try:
            if not any(self.preset_list[self.preset_index]):
                self.preset_entry.config({"background": "Red"})
            elif self.preset_list[self.preset_index]:
                self.preset_entry.config({"background": "Green"})
        except IndexError:
            self.preset_entry.config({"background": "Red"})
        self.update_preset_sliders()

    def load_preset(self):
        try:
            slider_list_values = self.preset_list[self.preset_index]
            self.name_field_text.set(self.preset_name_list[self.preset_index])
        except IndexError:
            slider_list_values = [0] * self.slider_amount
        for i in range(len(slider_list_values)):
            self.slider_list[i].set(int(slider_list_values[i]))

    def get_slider_information(self):
        if self.blackout_value != self.blackout_value_previous:
            if self.blackout_value:
                for i in range(len(self.slider_list)):
                    self.interface.send_signal(i + 1, 0)
            else:
                slider_list_values = [slider.get() for slider in self.slider_list]
                slider_list_values.append(self.grand_master.get())
                if int(self.grand_master.get()) != int(self.grand_master_manual_entry.get()):
                    self.grand_master_manual_stringvar.set(self.grand_master.get())
                for i in range(len(self.slider_list)):
                    slider = self.slider_list[i]
                    if int(slider.get()) != int(self.manual_entry_list[i].get()):
                        self.manual_entry_list[i].set(slider.get())
                    value = slider.get() * self.grand_master.get() // 255
                    self.interface.send_signal(i + 1, value)
                self.last_slider_list_values = slider_list_values
                if self.count > 10:
                    self.interface.reopen()
                    self.count = 0
                self.count += 1
            self.blackout_value_previous = self.blackout_value
        elif not self.blackout_value:
            slider_list_values = [slider.get() for slider in self.slider_list]
            slider_list_values.append(self.grand_master.get())
            if int(self.grand_master.get()) != int(self.grand_master_manual_entry.get()):
                self.grand_master_manual_stringvar.set(self.grand_master.get())
            if self.last_slider_list_values != slider_list_values:
                for i in range(len(self.slider_list)):
                    slider = self.slider_list[i]
                    if int(slider.get()) != int(self.manual_entry_list[i].get()):
                        self.manual_entry_list[i].set(slider.get())
                    value = slider.get() * self.grand_master.get() // 255
                    self.interface.send_signal(i + 1, value)
                self.last_slider_list_values = slider_list_values
            if self.count > 10:
                self.interface.reopen()
                self.count = 0
            self.count += 1
        self.editor_frame.after(1, self.get_slider_information)

    def backspace_handle(self, event):
        entry_field = self.editor_frame.focus_get()
        value = str(entry_field.get())
        if entry_field == self.grand_master_manual_entry:
            if len(value) != 1:
                self.grand_master_manual_stringvar.set(str(entry_field.get())[:len(value)])
            else:
                self.grand_master_manual_stringvar.set("0")
            return
        elif entry_field == self.preset_entry:
            if len(value) != 1:
                self.preset_entry_text.set(str(entry_field.get())[:len(value)])
            else:
                self.preset_entry_text.set("0")
            return
        index = self.entry_list.index(entry_field)
        if len(value) != 1:
            self.manual_entry_list[index].set(str(entry_field.get())[:len(value)])
        else:
            self.manual_entry_list[index].set("0")

    @staticmethod
    def integer_verify(action, index, value_if_allowed,
                       prior_value, text, validation_type, trigger_type, widget_name):
        if text in '0123456789':
            try:
                float(value_if_allowed)
                return True
            except ValueError:
                return False
        else:
            return False

    def limit_manual_entry_size(self, *args):
        entry_location = self.editor_frame.focus_get()
        if entry_location in self.entry_list:
            slider_no = self.entry_list.index(entry_location)
            if int(self.slider_list[slider_no].get()) != int(entry_location.get()):
                self.slider_list[slider_no].set(int(entry_location.get()))
            if len(entry_location.get()) > 3:
                self.manual_entry_list[slider_no].set(entry_location.get()[:3])
            if str(entry_location.get()[0]) == "0" and len(entry_location.get()) > 1:
                self.manual_entry_list[slider_no].set(entry_location.get()[1:])
        if not int(self.grand_master_manual_stringvar.get()) == int(self.grand_master.get()):
            self.grand_master.set(int(self.grand_master_manual_stringvar.get()))
        if len(self.grand_master_manual_stringvar.get()) > 3:
            self.grand_master_manual_stringvar.set(self.grand_master_manual_stringvar.get()[:3])
        if str(self.grand_master_manual_stringvar.get())[0] == "0" and len(self.grand_master_manual_stringvar.get()) > 1:
            self.grand_master_manual_stringvar.set(self.grand_master_manual_stringvar.get()[1:])
        if entry_location == self.preset_entry:
            if len(entry_location.get()) > self.preset_box_length - 1:
                self.preset_entry_text.set(entry_location.get()[:self.preset_box_length])
            if str(entry_location.get()[0]) == "0" and len(entry_location.get()) > 1:
                self.preset_entry_text.set(entry_location.get()[1:])
            if self.preset_index != int(entry_location.get()):
                self.preset_index = int(entry_location.get())
                try:
                    if not any(self.preset_list[self.preset_index]):
                        self.preset_entry.config({"background": "Red"})
                    elif self.preset_list[self.preset_index]:
                        self.preset_entry.config({"background": "Green"})
                except IndexError:
                    self.preset_entry.config({"background": "Red"})
                self.update_preset_sliders()

    def create_preset_frame(self):
        ...  # TODO

    def run(self):
        self.get_slider_information()
        self.master.mainloop()
    

if __name__ == '__main__':
    usbInterface = USBInterface()
    storageHandler = StorageHandler()
    gui = GUI(usbInterface, storageHandler)
    gui.run()
