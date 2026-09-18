const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const dataset = path.join("ai", "ui_detector", "dataset");

const trainImages = path.join(dataset, "train", "images");
const trainLabels = path.join(dataset, "train", "labels");
const valImages = path.join(dataset, "val", "images");
const valLabels = path.join(dataset, "val", "labels");

for (const dir of [trainImages, trainLabels, valImages, valLabels]) {
    fs.mkdirSync(dir, { recursive: true });
}

const pageVariants = [
    ["Registration Form", 3],
    ["Login Form", 2],
    ["Contact Form", 4],
    ["Profile Form", 5],
    ["Application Form", 6]
];

async function main() {
    const browser = await chromium.launch();

    for (let i = 0; i < 600; i++) {
        const [title, fieldCount] =
            pageVariants[i % pageVariants.length];

        const fields = [];

        for (let j = 0; j < fieldCount; j++) {
            fields.push(`
                <label>Field ${j + 1}</label>
                <input type="text" placeholder="Enter value">
            `);
        }

        const html = `
        <html>
        <head>
        <style>
            * { box-sizing: border-box; }

            body {
                margin: 0;
                font-family: Arial;
                background: hsl(${i * 37 % 360}, 20%, 94%);
                padding: ${30 + (i % 4) * 15}px;
            }

            .card {
                width: ${520 + (i % 5) * 80}px;
                margin: auto;
                background: white;
                padding: ${25 + (i % 3) * 10}px;
                border-radius: ${8 + (i % 4) * 4}px;
            }

            h1 {
                font-size: ${26 + (i % 3) * 4}px;
            }

            label {
                display: block;
                margin-top: 16px;
                margin-bottom: 6px;
            }

            input {
                display: block;
                width: 100%;
                height: ${38 + (i % 3) * 8}px;
                padding: 8px;
            }

            button {
                margin-top: 22px;
                padding: 12px 28px;
                font-size: 16px;
            }
        </style>
        </head>

        <body>
            <div class="card">
                <h1>${title}</h1>
                ${fields.join("")}
                <button>Submit</button>
            </div>
        </body>
        </html>
        `;

        const page = await browser.newPage({
            viewport: {
                width: 1280,
                height: 720
            }
        });

        await page.setContent(html);
        await page.waitForTimeout(100);

        const elements = await page.evaluate(() => {
            const items = [];

            document.querySelectorAll("input").forEach(el => {
                const r = el.getBoundingClientRect();
                items.push({
                    classId: 0,
                    x: r.x,
                    y: r.y,
                    width: r.width,
                    height: r.height
                });
            });

            document.querySelectorAll("button").forEach(el => {
                const r = el.getBoundingClientRect();
                items.push({
                    classId: 1,
                    x: r.x,
                    y: r.y,
                    width: r.width,
                    height: r.height
                });
            });

            return items;
        });

        const fileName = `ui_${String(i + 1).padStart(3, "0")}.png`;

        const isValidation = i >= 500;

        const imageDir = isValidation ? valImages : trainImages;
        const labelDir = isValidation ? valLabels : trainLabels;

        await page.screenshot({
            path: path.join(imageDir, fileName)
        });

        const labels = elements.map(el => {
            const centerX = (el.x + el.width / 2) / 1280;
            const centerY = (el.y + el.height / 2) / 720;
            const width = el.width / 1280;
            const height = el.height / 720;

            return `${el.classId} ${centerX} ${centerY} ${width} ${height}`;
        });

        fs.writeFileSync(
            path.join(
                labelDir,
                fileName.replace(".png", ".txt")
            ),
            labels.join("\n")
        );

        await page.close();
    }

    await browser.close();

    console.log("Generated 600 UI screenshots.");
    console.log("500 training images + 100 validation images.");
}

main();