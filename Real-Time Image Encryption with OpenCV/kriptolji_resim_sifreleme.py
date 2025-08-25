import cv2
import sqlite3
import numpy as np
from tkinter import *
from PIL import Image, ImageTk
from io import BytesIO

# Veritabanı bağlantısı
conn = sqlite3.connect("images.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original BLOB,
    encrypted BLOB,
    ascii_text TEXT
)""")
conn.commit()

# Her pikseli harfe dönüştürüp gruplayarak yeni bir görüntü oluştur
def symbol_encrypt(image):
    h, w, c = image.shape
    flattened_pixels = image.reshape((-1, 3))
    alphabet = [chr(i) for i in range(65, 91)] + [chr(i) for i in range(97, 123)]
    ascii_map = {}
    grouped_pixels = {char: [] for char in alphabet}

    for idx, pixel in enumerate(flattened_pixels):
        ascii_char = alphabet[idx % len(alphabet)]
        grouped_pixels[ascii_char].append(pixel)
        ascii_map[str(pixel.tolist())] = ascii_char

    all_pixels = []
    ascii_text = ""
    for char in alphabet:
        pixels = grouped_pixels[char]
        all_pixels.extend(pixels)
        ascii_text += char * len(pixels)

    new_h = int(np.sqrt(len(all_pixels)))
    new_w = new_h
    all_pixels = all_pixels[:new_h * new_w]
    new_image = np.array(all_pixels, dtype=np.uint8).reshape((new_h, new_w, 3))

    return new_image, ascii_text

def update_frame():
    global frame, encrypted_img, ascii_text
    ret, frame = cap.read()
    if ret:
        encrypted_img, ascii_text = symbol_encrypt(frame)

        if show_camera.get():
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(rgb).resize((350, 200)))
            lbl_video.imgtk = img
            lbl_video.configure(image=img)
        else:
            lbl_video.configure(image="")

        encrypted_rgb = cv2.cvtColor(encrypted_img, cv2.COLOR_BGR2RGB)
        encrypted_img_tk = ImageTk.PhotoImage(Image.fromarray(encrypted_rgb).resize((350, 200)))
        lbl_encrypted.imgtk = encrypted_img_tk
        lbl_encrypted.configure(image=encrypted_img_tk)

    lbl_video.after(10, update_frame)

def save_to_db():
    global frame, encrypted_img, ascii_text
    if frame is None or encrypted_img is None:
        return
    _, original_bytes = cv2.imencode('.png', frame)
    _, encrypted_bytes = cv2.imencode('.png', encrypted_img)
    ascii_text = ''.join([chr(pixel) for row in encrypted_img for pixel in row[:, 0]])[:500]
    cursor.execute("INSERT INTO images (original, encrypted, ascii_text) VALUES (?, ?, ?)",
                   (original_bytes.tobytes(), encrypted_bytes.tobytes(), ascii_text))
    conn.commit()

def read_from_db():
    cursor.execute("SELECT original, encrypted, ascii_text FROM images")
    records = cursor.fetchall()
    if not records:
        return

    top = Toplevel()
    top.title("Veritabanı Kayıtları")

    for idx, (original, encrypted, ascii_text) in enumerate(records):
        orig_img = Image.open(BytesIO(original)).resize((160, 120))
        enc_img = Image.open(BytesIO(encrypted)).resize((160, 120))

        orig_photo = ImageTk.PhotoImage(orig_img)
        enc_photo = ImageTk.PhotoImage(enc_img)

        Label(top, text=f"🔓 Orijinal Görsel {idx+1}").grid(row=idx*4, column=0)
        Label(top, image=orig_photo).grid(row=idx*4+1, column=0)
        Label(top, text=f"🔐 Şifreli Görsel {idx+1}").grid(row=idx*4, column=1)
        Label(top, image=enc_photo).grid(row=idx*4+1, column=1)

        Label(top, text="🧾 ASCII Temsilcisi:").grid(row=idx*4+2, column=0, columnspan=2)
        ascii_text_widget = Text(top, height=5, width=80, wrap=WORD)
        ascii_text_widget.insert(END, ascii_text if ascii_text else "ASCII verisi yok.")
        ascii_text_widget.config(state=DISABLED)
        ascii_text_widget.grid(row=idx*4+3, column=0, columnspan=2, pady=(0, 10))

        top.grid_slaves(row=idx*4+1, column=0)[0].image = orig_photo
        top.grid_slaves(row=idx*4+1, column=1)[0].image = enc_photo

def clear_database():
    cursor.execute("DELETE FROM images")
    conn.commit()
    print("Veritabanı temizlendi.")

# Arayüz
root = Tk()
root.title("🎥 Görüntü Şifreleme Sistemi")
root.geometry("500x500")

# Arka plan resmi
bg_image = Image.open("C:/Users/sulta/Desktop/background.png").resize((1500, 1500))
bg_photo = ImageTk.PhotoImage(bg_image)
bg_label = Label(root, image=bg_photo)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# Kamera göstergesi Checkbox
show_camera = BooleanVar(value=True)
chk_btn = Checkbutton(root, text="🎥 Kamerayı Göster", variable=show_camera, bg="#e0e0e0", font=("Arial", 10, "bold"))
chk_btn.pack(pady=5)

# Video gösterim
lbl_video = Label(root, bg="white")
lbl_video.pack(pady=10)

# Şifrelenmiş görüntü
lbl_encrypted = Label(root, bg="white")
lbl_encrypted.pack(pady=10)

btn_save = Button(root, text="💾 Kaydet", bg="#A3C9A8", fg="black", font=("Arial", 10, "bold"), command=save_to_db)
btn_save.pack(pady=5)

btn_read = Button(root, text="📂 Oku", bg="#F9D5E5", fg="black", font=("Arial", 10, "bold"), command=read_from_db)
btn_read.pack(pady=5)

btn_clear = Button(root, text="🗑️ Veri Tabanını Temizle", bg="#FFDDC1", fg="black", font=("Arial", 10, "bold"), command=clear_database)
btn_clear.pack(pady=5)

cap = cv2.VideoCapture(0)
frame = None
encrypted_img = None
ascii_text = ""
update_frame()

root.mainloop()
cap.release()
conn.close()
