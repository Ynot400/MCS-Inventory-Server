// scan_barcode.js

import Quagga from '/lib/quaggaJS/quagga.min.js'; 

Quagga.init({
    inputStream: {
        name: "Live",
        type: "LiveStream",
        target: document.querySelector("#camera"),
    },
    decoder: {
        readers: ["ean_reader"], // or other barcode types you want to support
    },
}, function (err) {
    if (err) {
        console.error("Error initializing Quagga:", err);
        return;
    }
    console.log("Quagga initialization finished. Ready to start.");
    Quagga.start();
});

// Attach the event handler for detected barcodes
Quagga.onDetected((result) => {
    const barcode = result.codeResult.code;
    document.querySelector("#result").innerText = `Scanned barcode: ${barcode}`;
});
