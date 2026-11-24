# AC-Antrieb: Frequenzumrichter + Asynchronmotor mit PID-Regelung

Simulation eines Frequenzumrichter-Antriebs (Praktikum ABB).

Starten: `python main.py` (benötigt `pygame` und `numpy`).

## Bedienung

| Eingabe | Wirkung |
|---|---|
| Start / Stop / Leertaste | Simulation laufen lassen / anhalten |
| Reset / R | alles auf Anfang |
| Einst. / S | Einstellungen (Zeitfenster, Rampe, J, U/f, PWM-Frequenz, Sim-Tempo) |
| B (halten) | mechanische Bremse |
| Slider | Last, Drehzahl-Sollwert, Messrauschen, Kp / Ki / Kd |
| Esc | Beenden |

Für grosse Bildschirme in `main.py` `SCALE = 1.0` setzen. Bei laufendem
Motor stroboskopiert die Rotoranimation. Dann in den Einstellungen das
Sim-Tempo auf z. B. 0.05 stellen (Zeitlupe).

## Dateien

| Datei | Inhalt |
|---|---|
| `main.py` | Fenster, Bedienung, Zeichnen |
| `simulation.py` | Gesamtsystem und Regelung (läuft ohne pygame) |
| `ac_drive.py` | Netz, Diodengleichrichter, Vorladung, Zwischenkreis, PWM-Wechselrichter, Brems-Chopper |
| `motor.py` | Asynchronmaschine (dynamisches Modell im alpha/beta-System) |
| `rotor.py` | Mechanik der Welle + Darstellung des Rotors |
| `brake.py` | Reibungsbremse mit Haftmodell |
| `pid.py` | PID-Regler (Anti-Windup, gefilterter D-Anteil auf Messwert) |
| `pygmonitor.py` | Grafen und Scope |
| `slider.py`, `coil.py`, `fonts.py` | Bedienelemente / Darstellung |

## Physik

**Umrichter:** 400-V-Netz → B6-Diodengleichrichter → Zwischenkreis
(C = 1 mF, ca. 563 V) → 2-Level-Wechselrichter mit Sinus-Dreieck-PWM
(2 kHz) und Nullsystem-Einspeisung (wie Raumzeigermodulation). Beim
Einschalten lädt ein Vorladewiderstand den Kondensator. Speist der Motor
beim Bremsen zurück, schaltet über 750 V ein Bremswiderstand zu.

**Motor:** 4-kW-Asynchronmotor, 4-polig (p = 2). Zustände: Ständerstrom
und Rotorfluss. Kontrolle am starren 50-Hz-Netz: 1436 U/min bei
Nennmoment 26.7 Nm, 7.6 A, 4.4 kW, wie bei einem echten 4-kW-Motor.

**Regelung (alle 0.5 ms), Kaskade:**
Sollwert → Rampe → Drehzahl-PID → Momentsollwert (max. 40 Nm)
→ Moment-PI mit Vorsteuerung → Schlupffrequenz (max. 30 rad/s)
→ Statorfrequenz = p·ω + ω_Schlupf → U/f-Kennlinie (6.5 V/Hz + Anhebung) → PWM.

**Zeitschritt:** 20 µs für Elektrik und Mechanik.
