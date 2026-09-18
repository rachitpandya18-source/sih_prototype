const { createWorker } = require("tesseract.js");

async function extractOCR(imagePath) {
    const worker = await createWorker("eng");

    const result = await worker.recognize(
        imagePath,
        {},
        {
            text: true,
            blocks: true
        }
    );

    const data = result.data;

    const words = [];

    for (const block of data.blocks || []) {
        for (const paragraph of block.paragraphs || []) {
            for (const line of paragraph.lines || []) {
                for (const word of line.words || []) {
                    words.push({
                        text: word.text,
                        x0: word.bbox.x0,
                        y0: word.bbox.y0,
                        x1: word.bbox.x1,
                        y1: word.bbox.y1
                    });
                }
            }
        }
    }

    await worker.terminate();

    return {
        text: data.text,
        words: words
    };
}

async function main() {
    const imagePath = process.argv[2];

    if (!imagePath) {
        console.log("Usage: node ai/ocr/ocr.js <image-path>");
        return;
    }

    const result = await extractOCR(imagePath);

    console.log(JSON.stringify(result));
}

main();