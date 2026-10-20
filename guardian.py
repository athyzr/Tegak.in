import time, ctypes
import cv2, numpy as np, tkinter as tk
import mediapipe as mp
import pystray
from PIL import Image, ImageDraw, ImageGrab, ImageFilter, ImageTk

import socket, sys
_lock = socket.socket()
try:
    _lock.bind(("127.0.0.1", 47653))
except OSError:
    sys.exit(0)                      # sudah ada yang berjalan
if sys.executable.lower().endswith("pythonw.exe"):
    sys.stderr = open("error.log", "a", buffering=1)

ctypes.windll.shcore.SetProcessDpiAwareness(1)

# ---- Pengaturan ----
CALIB_CM = 50
MIN_CM = 40
NECK_MIN = 0.82          # < 82% baseline = DANGER
NECK_WARN = 0.90         # < 90% baseline = WASPADA (mulai bungkuk)
SHOULDER_TILT_MAX = 8
HEAD_TILT_MAX = 12
BAD_SEC, GOOD_SEC = 3.0, 1.0
CALIB_SEC = 3
AWAY_SEC = 10            # tidak terdeteksi 10 detik = meja kosong
TICK_MS, TICK_AWAY_MS = 100, 1000
SNOOZE_SEC = 60
WIN = "Tegak-in"
DIST_WARN = 45           # < 45 cm = WASPADA "mulai mendekat"
POPUP_AFTER_SEC = 2      # masalah bertahan 2 detik -> popup
POPUP_COOLDOWN = 30      # jeda minimal antar popup (detik)
POPUP_SHOW_SEC = 4

pose = mp.solutions.pose.Pose(model_complexity=0,
                              min_detection_confidence=0.5,
                              min_tracking_confidence=0.5)
NOSE, L_EAR, R_EAR, L_SH, R_SH = 0, 7, 8, 11, 12
FONT = cv2.FONT_HERSHEY_SIMPLEX
COL = {0: (80, 200, 80), 1: (0, 200, 255), 2: (60, 60, 255),
       "calib": (255, 200, 0), "none": (170, 170, 170)}          # BGR (untuk OpenCV)
TRAY = {"active": (60, 180, 75), "danger": (220, 50, 50), "paused": (255, 150, 0),
        "away": (140, 140, 140), "calib": (50, 130, 255)}        # RGB (untuk tray)

def open_cam():
    c = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    c.set(3, 640); c.set(4, 480)
    return c

cap = open_cam()
for _ in range(10):
    if cap.isOpened(): break
    time.sleep(3); cap = open_cam()
root = tk.Tk(); root.withdraw()
overlay = None
cmds = []                # perintah dari tray (thread lain) -> diproses di tick()
st = dict(t0=time.time(), samples=[], sw0=None, neck0=None, bad=None, good=None,
          snooze=0, last_seen=time.time(), paused=False, show=True, win=False,
          quit=False, tray=None, warn_since=None, last_popup=0 )

# ---------------- System tray ----------------
def make_icon(rgb):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((4, 4, 60, 60), fill=rgb + (255,))
    return img

def set_tray(state):
    if st["tray"] == state: return
    st["tray"] = state
    icon.icon = make_icon(TRAY[state])
    icon.title = f"Tegak-in: {state}"

menu = pystray.Menu(
    pystray.MenuItem("Tampilkan kamera", lambda i, it: cmds.append("show"),
                     checked=lambda it: st["show"]),
    pystray.MenuItem(lambda it: "Lanjutkan" if st["paused"] else "Jeda",
                     lambda i, it: cmds.append("pause")),
    pystray.MenuItem("Kalibrasi ulang", lambda i, it: cmds.append("calib")),
    pystray.MenuItem("Snooze 60 detik", lambda i, it: cmds.append("snooze")),
    pystray.MenuItem("Keluar", lambda i, it: cmds.append("quit")),
)
icon = pystray.Icon("tegakin", make_icon(TRAY["calib"]), "Tegak-in", menu)
icon.run_detached()

# ---------------- Pengukuran ----------------
def tilt_deg(a, b):
    d = a - b
    t = abs(np.degrees(np.arctan2(d[1], d[0])))
    return 180 - t if t > 90 else t

def measure(frame):
    """return (hadir, data). hadir=False -> orangnya tidak ada di depan kamera."""
    h, w = frame.shape[:2]
    res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if not res.pose_landmarks: return False, None
    lm = res.pose_landmarks.landmark
    if lm[NOSE].visibility < 0.5: return False, None
    if min(lm[L_SH].visibility, lm[R_SH].visibility) < 0.5: return True, None
    P = lambda i: np.array([lm[i].x * w, lm[i].y * h])
    nose, ls, rs = P(NOSE), P(L_SH), P(R_SH)
    sw = np.linalg.norm(ls - rs)
    mid = (ls + rs) / 2
    head = None
    if min(lm[L_EAR].visibility, lm[R_EAR].visibility) > 0.5:
        head = tilt_deg(P(L_EAR), P(R_EAR))
    return True, dict(nose=nose, ls=ls, rs=rs, mid=mid, sw=sw,
                      neck=(mid[1] - nose[1]) / sw, tilt=tilt_deg(ls, rs), head=head)

# ---------------- Tampilan ----------------
def banner(frame, text, col, scale, sub=""):
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 90 if sub else 55), (25, 25, 25), -1)
    cv2.putText(frame, text, (12, 38), FONT, scale, col, 2)
    if sub: cv2.putText(frame, sub, (12, 76), FONT, 0.6, (235, 235, 235), 1)

def skeleton(frame, m, col):
    pt = lambda p: tuple(p.astype(int))
    cv2.line(frame, pt(m["ls"]), pt(m["rs"]), col, 4)
    cv2.line(frame, pt(m["mid"]), pt(m["nose"]), col, 4)
    for p in (m["ls"], m["rs"], m["nose"]):
        cv2.circle(frame, pt(p), 8, col, -1)

def close_win():
    if st["win"]:
        try: cv2.destroyWindow(WIN)
        except cv2.error: pass
        st["win"] = False

def show_overlay(reason):
    global overlay
    if overlay: return
    img = ImageGrab.grab()
    W, H = img.size
    blur = img.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(6)).resize((W, H))
    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)
    overlay.attributes("-topmost", True)
    overlay.geometry(f"{W}x{H}+0+0")
    photo = ImageTk.PhotoImage(blur)
    lbl = tk.Label(overlay, image=photo); lbl.image = photo; lbl.pack()
    tk.Label(overlay, text=f"DANGER: {reason}\nTegakkan badan & atur jarak\n(Esc = snooze 60 detik)",
             font=("Segoe UI", 28, "bold"), fg="white", bg="#aa2222").place(relx=.5, rely=.5, anchor="center")
    overlay.bind("<Escape>", lambda e: snooze())
    overlay.focus_force()

def hide_overlay():
    global overlay
    if overlay: overlay.destroy(); overlay = None

def snooze():
    st["snooze"] = time.time() + SNOOZE_SEC
    hide_overlay()

def show_popup(text):
    p = tk.Toplevel(root)
    p.overrideredirect(True)
    p.attributes("-topmost", True)
    p.configure(bg="#ff9800")
    tk.Label(p, text=text, font=("Segoe UI", 14, "bold"), fg="white",
             bg="#ff9800", padx=24, pady=16).pack()
    p.update_idletasks()
    W, H = p.winfo_width(), p.winfo_height()
    sw, sh = p.winfo_screenwidth(), p.winfo_screenheight()
    p.geometry(f"+{sw - W - 24}+{sh - H - 80}")
    p.after(POPUP_SHOW_SEC * 1000, p.destroy)

def recalibrate():
    st.update(t0=time.time(), samples=[], sw0=None, neck0=None, last_seen=time.time())

def run_cmds():
    global cap
    while cmds:
        c = cmds.pop(0)
        if c == "show": st["show"] = not st["show"]
        elif c == "snooze": snooze()
        elif c == "calib": recalibrate()
        elif c == "quit": st["quit"] = True
        elif c == "pause":
            st["paused"] = not st["paused"]
            if st["paused"]:
                cap.release(); hide_overlay(); close_win()
            else:
                cap = open_cam(); st["last_seen"] = time.time()

def shutdown():
    icon.stop(); cap.release(); cv2.destroyAllWindows(); root.destroy()

# ---------------- Loop utama ----------------
def tick():
    run_cmds()
    if st["quit"]: shutdown(); return
    if st["paused"]:
        set_tray("paused"); root.after(300, tick); return

    delay = TICK_MS
    ok, frame = cap.read()
    now = time.time()
    if ok:
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        hadir, m = measure(frame)
        if hadir: st["last_seen"] = now
        calibrating = st["sw0"] is None

        if calibrating:                                          # --- kalibrasi ---
            set_tray("calib")
            left = CALIB_SEC - (now - st["t0"])
            if m:
                st["samples"].append((m["sw"], m["neck"]))
                skeleton(frame, m, COL["calib"])
            banner(frame, f"KALIBRASI {max(left,0):.0f} | duduk tegak, {CALIB_CM} cm", COL["calib"], 0.75)
            if left <= 0:
                if len(st["samples"]) >= 5:
                    st["sw0"] = float(np.median([s[0] for s in st["samples"]]))
                    st["neck0"] = float(np.median([s[1] for s in st["samples"]]))
                else:
                    st["t0"] = now; st["samples"] = []

        elif now - st["last_seen"] > AWAY_SEC:                   # --- meja kosong ---
            set_tray("away"); hide_overlay()
            st["bad"] = st["good"] = None
            delay = TICK_AWAY_MS
            banner(frame, "Meja kosong - jeda otomatis", COL["none"], 0.75)

        elif m is None:                                          # --- bahu tak terlihat ---
            set_tray("active")
            banner(frame, "Bahu tidak terlihat - mundur sedikit", COL["none"], 0.75)
            st["bad"] = None

        else:                                                    # --- deteksi normal ---
            dist = CALIB_CM * st["sw0"] / m["sw"]
            neck_pct = m["neck"] / st["neck0"]
            danger, warn = [], []
            if dist < MIN_CM: danger.append("TERLALU DEKAT")
            if neck_pct < NECK_MIN: danger.append("BUNGKUK/MENUNDUK")
            elif neck_pct < NECK_WARN: warn.append("MULAI BUNGKUK")
            if m["tilt"] > SHOULDER_TILT_MAX: warn.append("BAHU MIRING")
            if m["head"] is not None and m["head"] > HEAD_TILT_MAX: warn.append("KEPALA MIRING")
            level = 2 if danger else (1 if warn else 0)
            col = COL[level]
            soft = [x for x in warn if x in ("MULAI BUNGKUK", "MULAI MENDEKAT")]
            if soft and not danger:
                st["warn_since"] = st["warn_since"] or now
                if (now - st["warn_since"] > POPUP_AFTER_SEC
                        and now - st["last_popup"] > POPUP_COOLDOWN
                        and now >= st["snooze"]):
                    show_popup(" & ".join(soft).capitalize() + "\nTegakkan badan / mundur sedikit")
                    st["last_popup"] = now
            else:
                st["warn_since"] = None
            set_tray("danger" if level == 2 else "active")

            skeleton(frame, m, col)
            banner(frame, ["AMAN", "WASPADA", "DANGER!"][level], col, 1.1,
                   f"Jarak {dist:.0f} cm | Leher {neck_pct*100:.0f}% | Bahu miring {m['tilt']:.0f} deg")
            if danger or warn:
                cv2.putText(frame, " + ".join(danger + warn), (12, h - 15), FONT, 0.7, col, 2)
            if level == 2:
                cv2.rectangle(frame, (0, 0), (w - 1, h - 1), col, 8)

            bad = level == 2 and now >= st["snooze"]
            if bad:
                st["good"] = None; st["bad"] = st["bad"] or now
                if now - st["bad"] > BAD_SEC: show_overlay(" + ".join(danger))
            else:
                st["bad"] = None; st["good"] = st["good"] or now
                if now - st["good"] > GOOD_SEC: hide_overlay()

        if st["show"]:
            cv2.putText(frame, "c=kalibrasi ulang  q=keluar", (w - 260, h - 15), FONT, 0.5, (200, 200, 200), 1)
            cv2.imshow(WIN, frame); st["win"] = True
        else:
            close_win()

    k = cv2.waitKey(1) & 0xFF
    if k == ord("q"): st["quit"] = True
    if k == ord("c"): recalibrate()
    if st["win"] and cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
        st["show"] = False; close_win()                          # tombol X = sembunyikan ke tray
    root.after(delay, tick)

tick()
root.mainloop()