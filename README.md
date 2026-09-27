# ISI Wave & Structure Engine — Python Backend

Yeh ek **alag, chhota Python server** hai jo 24/7 chalke crypto + forex/gold/indices
ka real price data leta hai, **Elliott Wave** aur **Smart Money Concepts (SMC)**
dono ke rules laga ke ek "confluence report" banata hai, aur usse seedha
tumhare **existing Firebase** (wahi jo ISI Terminal app use karta hai) mein
push kar deta hai — Firebase path: `isi_v6/engine_output/{instrument}`.

Frontend (zone-report-widget.js jaisa pattern) isko live padh sakta hai, koi
polling ya extra setup ki zaroorat nahi.

---

## 1. Deploy karne ke steps (Render — free)

1. [render.com](https://render.com) pe free account banao (GitHub se sign in kar sakte ho)
2. Is `python-engine/` folder ko **ek alag GitHub repo** mein daalo (isi terminal ke static site wale repo se ALAG rakhna — yeh Python hai, wo static HTML hai)
3. Render dashboard → **New → Web Service** → apna naya repo select karo
4. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. **Create Web Service** dabao — 2-3 min mein deploy ho jayega
6. Deploy hone ke baad ek URL milega jaisे `https://isi-wave-engine.onrender.com`

## 2. Engine ko 24/7 zinda rakhna (IMPORTANT)

Render ka **free tier 15 minute** ke baad service ko **sula deta hai** agar koi
HTTP request na aaye. Isse bachne ke liye:

1. [cron-job.org](https://cron-job.org) pe free account banao (koi credit card nahi)
2. Ek naya cron job banao: **har 10 minute** mein tumhare Render URL ka
   `/health` endpoint hit kare — e.g. `https://isi-wave-engine.onrender.com/health`
3. Bas — ab service kabhi nahi sotii, background loop hamesha chalta rahega

## 3. Verify karna

- `https://isi-wave-engine.onrender.com/` → engine chal raha hai, instrument list dikhega
- `https://isi-wave-engine.onrender.com/status` → last update time + har instrument ka status
- Firebase Console → Realtime Database → `isi_v6/engine_output/` → live data aana chahiye 1-2 min mein

---

## Patterns kaise mark hote hain (poora logic yahi hai)

### Zigzag Swings (sabki foundation)
Price ke turning points (swing high/low) nikalte hain. Threshold instrument
ki apni volatility (ATR) se khud decide hota hai — BTC ka 1% move aur
EUR/USD ka 1% move barabar nahi hote, isliye hardcoded % nahi rakha.

### Elliott Wave (5 rules)
Last 6 swing pivots leke unhe **Wave 0-1-2-3-4-5** naam dete hain, phir teen
**hard rules** check karte hain:
1. Wave 2, Wave 1 ke start se aage retrace nahi kar sakti
2. Wave 3, waves 1/3/5 mein sabse chhoti nahi ho sakti
3. Wave 4, Wave 1 ke price range ko overlap nahi kar sakti

Teeno rules pass ho to "valid impulse" bolte hain, phir Fibonacci ratios
(Wave3/Wave1 ≈1.618, Wave2 retrace ≈50-61.8%, Wave4 retrace ≈38-50%) check
karke confidence score badhate hain. **Yeh guaranteed prediction nahi hai** —
Elliott Wave khud subjective field hai, isliye hum sirf "kitna clean count
hai" ka confidence deते hain, "yeh hi hoga" nahi.

### Smart Money Concepts
- **BOS** (Break of Structure): price apne hi trend ki direction mein pichhle
  swing ko close karke todta hai → trend continue
- **CHoCH** (Change of Character): price ULTI direction ke pichhle swing ko
  todta hai → possible reversal warning
- **Order Block**: BOS/CHoCH se pehle ka aakhri opposite-colour candle
- **FVG** (Fair Value Gap): 3-candle gap jahan candle 1 aur candle 3 ke beech
  price nahi chhua gaya — yeh "magnet zone" ki tarah kaam karta hai
- **Liquidity Zone**: do ya zyada swing points jo bahut close price pe hain
  (0.1% ke andar) — yahan retail stop-losses cluster hote hain

### Confluence Score (final number)
Elliott Wave + SMC dono ka signal same direction mein ho to score badhta
hai, opposite ho ya CHoCH aaye to ghatta hai. **Yeh probability nahi,
confluence hai** — kitne independent signals ek saath agree kar rahe hain,
uska measure. Market kabhi bhi isse invalidate kar sakta hai.

---

## Files

| File | Kaam |
|---|---|
| `main.py` | FastAPI app + background loop jo har instrument ko cycle karta hai |
| `engine/instruments.py` | Tracked instruments ki list (naya instrument add karna ho to bas yahan ek line) |
| `engine/data_feed.py` | Binance (crypto) + Stooq (forex/gold/indices) se seedha data — no proxy chahiye, server-side hai |
| `engine/swings.py` | Zigzag swing pivot detector |
| `engine/elliott_wave.py` | Elliott Wave rule-based labeler |
| `engine/smc.py` | BOS/CHoCH/Order Block/FVG/Liquidity detector |
| `engine/probability.py` | Sab combine karke final confluence score |
| `engine/firebase_writer.py` | Firebase mein result push karta hai |

## Naya instrument add karna ho

`engine/instruments.py` mein ek line add karo — bas. Baaki sab automatic
chalega.
