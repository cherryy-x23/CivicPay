import cv2
import zxingcpp


def extract_qr_data(image_path: str):

    try:

        image = cv2.imread(image_path)

        if image is None:
            return {
                "detected": False,
                "is_payment_qr": False,
                "data": None,
                "type": None
            }

        results = zxingcpp.read_barcodes(image)

        if not results:
            return {
                "detected": False,
                "is_payment_qr": False,
                "data": None,
                "type": None
            }

        qr = results[0]

        data = qr.text

        # Check whether QR contains a UPI payment link
        is_payment_qr = (
            data is not None
            and data.lower().startswith("upi://pay")
        )

        return {
            "detected": True,
            "is_payment_qr": is_payment_qr,
            "data": data,
            "type": str(qr.format)
        }

    except Exception as e:

        print("QR detection error:", e)

        return {
            "detected": False,
            "is_payment_qr": False,
            "data": None,
            "type": None
        }