from rembg import remove
from PIL import Image, ImageDraw
import cv2
import numpy as np
from datetime import datetime

class image_processing:
    def __init__(self, resolution = 80, save_img=True, save_pat = True, save_timestamp=True):
        '''
        Es muss nur die Funktion image_to_matrix ausgeführt werden!

        Resolution setzt die Anzahl Punkte pro Seite. Mit safe=False kann das Speichern aller Zwischenbilder im png Format unterbunden werden. Gleiches gilt für das Abspeichern der pat-Datei. Mit save_timestamp=False verhindert man, dass der Zeitpunkt des Renderings im Dateinamen ergänzt wird, sodass die Dateien überschrieben werden.
        '''
        self.res = resolution
        self.save = save_img
        self.save_pat = save_pat
        self.timestamp = save_timestamp
        self.timestamp_time = ""
        self.image_counter = 0
        pass

    def open_image(self, img):
        return Image.open(img)

    def remove_background(self, img):
        '''
        Entfernt den Hintergrund aus Bildern mit Personen (auch Personengruppen - sofern im Vordergrund).
        '''
        # Input Image laden
        input_image = img

        # Speichere originales Bild mit Hintergrund
        if self.save:
            self.save_img(input_image, "withbackground")

        # Hintergrund entfernen
        output_image = remove(input_image)

        # Speichere Bild ohne Hintergrund
        if self.save:
            self.save_img(output_image, "withoutbackground")

        return output_image

    def convert_to_alpha_grey(self, img):
        '''
        Extrahiert aus dem gegeben Bild ein Graustufen-, und ein Alphakanal-Array
        '''
        gray = np.array(img.convert("L"))
        alpha = np.array(img.getchannel("A"))
        return gray,alpha

    def crop_square(self, img):
        '''
        Skaliert das Bild in einer Quadrat mit der Pixelbreite der kleineren Seite. Der Mittelpunkt des Bildes bleibt dabei gleich!
        '''

        # Ermittle Breite und Höhe des Bildes und wähle das Minimum als neue Kantenlänge
        width, height = img.size
        size = min(width, height)

        # Ermittle was oben und links abgeschnitten werden muss
        left = (width - size) // 2
        top = (height - size) // 2

        # Schneide Bild zu
        img = img.crop((
            left,
            top,
            left + size,
            top + size
        ))

        return img   
    
    def draw_image(self, img, threshold=128):

        # Bild laden, falls ein Dateipfad übergeben wurde
        if not isinstance(img, Image.Image):
            img = Image.open(img)

        img = img.convert("RGBA")

        # Größe des Bildes
        width, height = img.size

        # Transparente Bereiche auf Weiß legen
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img).convert("L")

        # Bild reskalieren auf zuvor übergebene Pixelanzahl pro Seite
        small = img.resize(
            (self.res, self.res),
            Image.Resampling.BOX
        )

        if self.save:
                    self.save_img(small, "small")

        # Bildmatrix generieren
        pixels = np.array(small, dtype=np.float32)

        # Neue leere Bildmatrix
        matrix = np.zeros(
            (self.res, self.res),
            dtype=np.uint8
        )

        # Mit Floyd-Steinberg Algorithmus neue leere Bildmatrix aus ursprünglicher Matrix erreichen
        for y in range(self.res):
            for x in range(self.res):

                # Rechne alten Pixel in neuen Pixel über einen threshold um
                old_pixel = pixels[y, x]
                new_pixel = 0.0 if old_pixel < threshold else 255.0

                # Erstelle binäre Matrix aus dem neuen Pixel
                matrix[y, x] = 1 if new_pixel == 0 else 0

                # Fehler zwischen altem und neuen Pixel zur Manipulation umliegender Pixel
                error = old_pixel - new_pixel

                # Nächster Pixel der x-Koordinate (rechts daneben) wird erhöht oder reduziert, wenn dieser formal eine 0 liefert
                if x + 1 < self.res:
                    pixels[y, x + 1] += error * 7 / 16

                # Eine Zeile tiefer, sofern [y +1, x] weiß wäre, werden die drei darunter befindlichen Pixel anhand der Abweichung zwischen Wert des Ursprünglichen Pixels und dem neuen 0 oder 1 korrigiert
                if y + 1 < self.res:

                    # Sofern man sich nicht im ersten Pixel der Reihe befindet
                    if x > 0:
                        pixels[y + 1, x - 1] += error * 3 / 16

                    # Geht immer, da y+1 < resolution
                    pixels[y + 1, x] += error * 5 / 16

                    # Sofern man sich nicht am Ende der Reihe befindet
                    if x + 1 < self.res:
                        pixels[y + 1, x + 1] += error * 1 / 16

        # Sofern gespeichert werden soll
        if self.save:
            # Erstelle ein leeres Bild im 1 Bit-Modus (S/W) mit Hintergundfarbe weiß
            output = Image.new("1", (width, height), 1)
            draw = ImageDraw.Draw(output)

            # Ermittle Abstand zwischen den Rasterpositionen (ist für x und y gleich)
            spacing = width / self.res

            # Ermittle sinnvollen Punktradius
            dot_radius = 0.7 * spacing / 2

            # Rastere alle Elemente im Array ab und zeichne für alle 1 einen schwarzen Punkt
            for y in range(self.res):
                for x in range(self.res):

                    if matrix[y, x] == 1:

                        center_x = int((x + 0.5) * spacing)
                        center_y = int((y + 0.5) * spacing)

                        draw.ellipse(
                            (
                                center_x - dot_radius,
                                center_y - dot_radius,
                                center_x + dot_radius,
                                center_y + dot_radius
                            ),
                            fill=0
                        )
            # Speichern
            self.save_img(output, "dotimage")

        # Abspeichern der Matrix im pat-Format
        if self.save_pat:
            if self.timestamp:
                file_name = "output/" + self.timestamp_time + "_dot_matrix.pat"
            else:
                file_name = "dot_matrix.pat"


            with open(file_name, "w") as file:
                for row in matrix[:80, :80]:
                    values = "".join(str(value) for value in row)

                    formatted = " ".join(
                        values[i:i+20]
                        for i in range(0, 80, 20)
                    )

                    file.write(formatted + "\n")

        return matrix

    def save_img(self, img, name):
        '''
        Speichert übergebenes Bild im png-Format. (Hat nur illustrative Zwecke xD)
        '''

        # Prüfe, ob timestamp gesetzt werden soll
        if self.timestamp:
            file_name =  self.timestamp_time + "_" + name

        else:
            file_name = name

        # Abspeichern
        img.save(f"output/{file_name}.png")

    def person_to_matrix(self, img):
        ''' 
        Leitet alle benötigten Schritte ein und gibt die Matrix als Numpy-Array zurück. Das Speichern der Dateien wird beim Aufrufen der Datei festgelegt.
        Es wird ein Bild einer Person im Vordergrund erwartet.
        Img muss als Dateipfad übergeben werden.
        '''
        # Setzt Timestamp für das Abspeichern der Bilder festlegen
        self.timestamp_time = datetime.now().strftime("%Y%m%d_%H%M%S") + str(self.image_counter)
        self.image_counter += 1

        # Falls während dem Prozess etwas schief geht, wird eine Nullmatrix zurückgegeben
        dot_matrix = matrix = np.zeros((self.res, self.res), dtype=np.uint8)

        try:
            # Bild öffnen
            opened_img = self.open_image(img)

            # Quadratisch zuschneiden
            cropped_image = self.crop_square(opened_img)
            
            # Hintergrund entfernen
            without_background = self.remove_background(cropped_image)
            
            # Generiere die Matrix
            dot_matrix = self.draw_image(without_background)

        except Exception as e:
            print(f"Fehler: {e}")

        return dot_matrix, self.timestamp_time

    def image_to_matrix(self, img):
            ''' 
            Leitet alle benötigten Schritte ein und gibt die Matrix als Numpy-Array zurück. Das Speichern der Dateien wird beim Aufrufen der Datei festgelegt.
            Das gesamte Bild wird umgerechnet. Objekte und Personen werden nicht ausgeschnitten.
            Img muss als Dateipfad übergeben werden.
            '''
            # Setzt Timestamp für das Abspeichern der Bilder festlegen
            self.timestamp_time = datetime.now().strftime("%Y%m%d_%H%M%S") + str(self.image_counter)
            self.image_counter += 1
    
            # Falls während dem Prozess etwas schief geht, wird eine Nullmatrix zurückgegeben
            dot_matrix = matrix = np.zeros((self.res, self.res), dtype=np.uint8)
    
            try:
                # Bild öffnen
                opened_img = self.open_image(img)

                # Quadratisch zuschneiden
                cropped_image = self.crop_square(opened_img)

                self.save_img(cropped_image, "original")
                
                # Generiere die Matrix
                dot_matrix = self.draw_image(cropped_image)
    
            except Exception as e:
                print(f"Fehler: {e}")
    
            return dot_matrix, self.timestamp_time