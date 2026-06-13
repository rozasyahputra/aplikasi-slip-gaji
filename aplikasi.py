import sqlite3
import gradio as gr
from fpdf import FPDF

DB = "gaji.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS karyawan
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nama TEXT NOT NULL,
                  nik TEXT UNIQUE,
                  jabatan TEXT,
                  departemen TEXT,
                  gaji_pokok REAL DEFAULT 0,
                  email TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS periode
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  bulan TEXT,
                  tahun INTEGER,
                  status TEXT DEFAULT 'draft')''')

    c.execute('''CREATE TABLE IF NOT EXISTS payroll
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  periode_id INTEGER,
                  karyawan_id INTEGER,
                  tunjangan REAL DEFAULT 0,
                  lembur REAL DEFAULT 0,
                  bpjs REAL DEFAULT 0,
                  pph REAL DEFAULT 0,
                  kasbon REAL DEFAULT 0,
                  gaji_bersih REAL DEFAULT 0,
                  FOREIGN KEY(periode_id) REFERENCES periode(id),
                  FOREIGN KEY(karyawan_id) REFERENCES karyawan(id))''')
    conn.commit()
    conn.close()

def get_karyawan():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, nama, nik, jabatan, departemen, gaji_pokok FROM karyawan ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return data

def tambah_karyawan(nama, nik, jabatan, departemen, gaji, email):
    if not nama:
        return "Nama wajib diisi", get_karyawan()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO karyawan (nama, nik, jabatan, departemen, gaji_pokok, email) VALUES (?,?,?,?,?,?)",
                  (nama, nik, jabatan, departemen, float(gaji), email))
        conn.commit()
        msg = "Berhasil tambah karyawan"
    except Exception as e:
        msg = f"Gagal: {str(e)}"
    conn.close()
    return msg, get_karyawan()

def hapus_karyawan(karyawan_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM karyawan WHERE id=?", (karyawan_id,))
    conn.commit()
    conn.close()
    return "Berhasil hapus", get_karyawan()

def update_karyawan(karyawan_id, nama, jabatan, departemen, gaji):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE karyawan SET nama=?, jabatan=?, departemen=?, gaji_pokok=? WHERE id=?",
              (nama, jabatan, departemen, float(gaji), karyawan_id))
    conn.commit()
    conn.close()
    return "Berhasil update", get_karyawan()

def get_periode():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, bulan, tahun, status FROM periode ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return data

def buat_periode(bulan, tahun):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO periode (bulan, tahun) VALUES (?,?)", (bulan, int(tahun)))
    periode_id = c.lastrowid
    c.execute("SELECT id FROM karyawan")
    for k in c.fetchall():
        c.execute("INSERT INTO payroll (periode_id, karyawan_id) VALUES (?,?)", (periode_id, k[0]))
    conn.commit()
    conn.close()
    return f"Periode {bulan} {tahun} dibuat", get_periode()

def get_payroll(periode_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT p.id, k.nama, k.jabatan, p.tunjangan, p.lembur, p.kasbon, p.gaji_bersih
                 FROM payroll p JOIN karyawan k ON p.karyawan_id=k.id
                 WHERE p.periode_id=?""", (periode_id,))
    data = c.fetchall()
    conn.close()
    return data

def hitung_gaji(payroll_id, tunjangan, lembur, kasbon):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT k.gaji_pokok, p.periode_id FROM payroll p JOIN karyawan k ON p.karyawan_id=k.id WHERE p.id=?", (payroll_id,))
    data = c.fetchone()
    if not data:
        return "Data tidak ditemukan", None
    gaji_pokok, periode_id = data

    gaji_kotor = float(gaji_pokok) + float(tunjangan) + float(lembur)
    bpjs = gaji_kotor * 0.01
    pph = gaji_kotor * 0.05
    gaji_bersih = gaji_kotor - bpjs - pph - float(kasbon)

    c.execute("UPDATE payroll SET tunjangan=?, lembur=?, kasbon=?, bpjs=?, pph=?, gaji_bersih=? WHERE id=?",
              (tunjangan, lembur, kasbon, bpjs, pph, gaji_bersih, payroll_id))
    conn.commit()
    conn.close()
    return f"Gaji bersih: Rp {int(gaji_bersih):,}", get_payroll(periode_id)

def buat_pdf(payroll_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT k.nama, k.jabatan, pr.bulan, pr.tahun, k.gaji_pokok,
                        p.tunjangan, p.lembur, p.bpjs, p.pph, p.kasbon, p.gaji_bersih
                 FROM payroll p
                 JOIN karyawan k ON p.karyawan_id=k.id
                 JOIN periode pr ON p.periode_id=pr.id
                 WHERE p.id=?""", (payroll_id,))
    data = c.fetchone()
    conn.close()

    if not data:
        return None

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'SLIP GAJI', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Nama: {data[0]}', 0, 1)
    pdf.cell(0, 10, f'Jabatan: {data[1]}', 0, 1)
    pdf.cell(0, 10, f'Periode: {data[2]} {data[3]}', 0, 1)
    pdf.ln(5)
    pdf.cell(100, 10, 'Gaji Pokok', 0, 0); pdf.cell(0, 10, f'Rp {int(data[4]):,}', 0, 1)
    pdf.cell(100, 10, 'Tunjangan', 0, 0); pdf.cell(0, 10, f'Rp {int(data[5]):,}', 0, 1)
    pdf.cell(100, 10, 'Lembur', 0, 0); pdf.cell(0, 10, f'Rp {int(data[6]):,}', 0, 1)
    pdf.cell(100, 10, 'BPJS', 0, 0); pdf.cell(0, 10, f'Rp {int(data[7]):,}', 0, 1)
    pdf.cell(100, 10, 'PPh 21', 0, 0); pdf.cell(0, 10, f'Rp {int(data[8]):,}', 0, 1)
    pdf.cell(100, 10, 'Kasbon', 0, 0); pdf.cell(0, 10, f'Rp {int(data[9]):,}', 0, 1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(100, 10, 'Gaji Bersih', 0, 0); pdf.cell(0, 10, f'Rp {int(data[10]):,}', 0, 1)

    filename = f"slip_{data[0].replace(' ', '_')}.pdf"
    pdf.output(filename)
    return filename

init_db()

with gr.Blocks(title="Aplikasi Slip Gaji") as app:
    gr.Markdown("# Aplikasi Slip Gaji")

    with gr.Tab("Karyawan"):
        with gr.Row():
            nama = gr.Textbox(label="Nama")
            nik = gr.Textbox(label="NIK")
        with gr.Row():
            jabatan = gr.Textbox(label="Jabatan")
            departemen = gr.Textbox(label="Departemen")
        with gr.Row():
            gaji = gr.Number(label="Gaji Pokok", value=0)
            email = gr.Textbox(label="Email")

        with gr.Row():
            btn_tambah = gr.Button("Tambah")
            btn_hapus = gr.Button("Hapus")
            btn_update = gr.Button("Update")

        status_karyawan = gr.Textbox(label="Status")
        tabel_karyawan = gr.Dataframe(headers=["ID", "Nama", "NIK", "Jabatan", "Departemen", "Gaji"],
                                      value=get_karyawan(), interactive=False)

        btn_tambah.click(tambah_karyawan,
                         inputs=[nama, nik, jabatan, departemen, gaji, email],
                         outputs=[status_karyawan, tabel_karyawan])

        karyawan_id_input = gr.Number(label="ID Karyawan untuk Hapus/Update", visible=False)
        tabel_karyawan.select(lambda evt: evt.index[0]+1 if evt.index else None, None, karyawan_id_input)
        btn_hapus.click(hapus_karyawan, inputs=[karyawan_id_input], outputs=[status_karyawan, tabel_karyawan])
        btn_update.click(update_karyawan,
                         inputs=[karyawan_id_input, nama, jabatan, departemen, gaji],
                         outputs=[status_karyawan, tabel_karyawan])

    with gr.Tab("Penggajian"):
        bulan = gr.Textbox(label="Bulan")
        tahun = gr.Number(label="Tahun", value=2026)
        btn_periode = gr.Button("Buat Periode")
        status_periode = gr.Textbox(label="Status")
        tabel_periode = gr.Dataframe(headers=["ID", "Bulan", "Tahun", "Status"], value=get_periode())
        btn_periode.click(buat_periode, inputs=[bulan, tahun], outputs=[status_periode, tabel_periode])

        gr.Markdown("### Hitung Gaji")
        periode_id = gr.Number(label="ID Periode")
        btn_load = gr.Button("Load Data Payroll")
        tabel_payroll = gr.Dataframe(headers=["ID", "Nama", "Jabatan", "Tunjangan", "Lembur", "Kasbon", "Gaji Bersih"])

        payroll_id = gr.Number(label="ID Payroll untuk Edit", visible=False)
        tunjangan = gr.Number(label="Tunjangan", value=0)
        lembur = gr.Number(label="Lembur", value=0)
        kasbon = gr.Number(label="Kasbon", value=0)
        btn_hitung = gr.Button("Hitung Gaji")
        hasil_hitung = gr.Textbox(label="Hasil")

        btn_load.click(get_payroll, inputs=[periode_id], outputs=[tabel_payroll])
        tabel_payroll.select(lambda evt: evt.index[0]+1 if evt.index else None, None, payroll_id)
        btn_hitung.click(hitung_gaji,
                         inputs=[payroll_id, tunjangan, lembur, kasbon],
                         outputs=[hasil_hitung, tabel_payroll])

        gr.Markdown("### Generate PDF")
        btn_pdf = gr.Button("Buat PDF")
        file_output = gr.File(label="Download")
        btn_pdf.click(buat_pdf, inputs=[payroll_id], outputs=[file_output])

app.launch()
