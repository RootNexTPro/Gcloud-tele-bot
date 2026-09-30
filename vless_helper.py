import urllib.parse
import qrcode
import io

def generate_vless_url(cloudrun_url: str) -> str:
    # cloudrun_url format: https://ahmed-vip1-xxxx.us-central1.run.app
    try:
        parsed_url = urllib.parse.urlparse(cloudrun_url)
        host = parsed_url.netloc
    except Exception:
        host = cloudrun_url

    vless_uri = f"vless://aaaa1111-bbbb-4ccc-8ddd-eeeeffff0000@alt13.yt3.ggpht.com:443?path=%2FTelegram%2F%40AM2_D3%2F%40AHMAD3214&security=tls&encryption=none&type=ws&host={host}&sni=alt13.yt3.ggpht.com#CloudRun-VIP"
    return vless_uri

def generate_qr_code(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return bio
