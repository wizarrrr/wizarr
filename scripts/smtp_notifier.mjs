import process from "node:process";

function writeResult(ok, error = null) {
  process.stdout.write(`${JSON.stringify({ ok, error })}\n`);
}

async function readStdin() {
  let input = "";
  for await (const chunk of process.stdin) {
    input += chunk;
  }
  return input;
}

function buildTransportConfig(payload) {
  const secure = payload.encryption === "ssl";
  return {
    host: payload.host,
    port: payload.port,
    secure,
    requireTLS: payload.encryption === "starttls",
    auth:
      payload.username && payload.password
        ? {
            user: payload.username,
            pass: payload.password,
          }
        : undefined,
  };
}

async function main() {
  let nodemailer;
  try {
    ({ default: nodemailer } = await import("nodemailer"));
  } catch (error) {
    writeResult(false, `Nodemailer import failed: ${error.message}`);
    process.exit(1);
  }

  let payload;
  try {
    payload = JSON.parse((await readStdin()) || "{}");
  } catch {
    writeResult(false, "Invalid SMTP payload JSON");
    process.exit(1);
  }

  if (!payload.host || !payload.fromEmail || !Array.isArray(payload.toEmails)) {
    writeResult(false, "Missing required SMTP fields")
    process.exit(1);
  }

  const recipients = payload.toEmails.map((email) => String(email).trim()).filter(Boolean);
  if (!recipients.length) {
    writeResult(false, "No valid recipient emails provided");
    process.exit(1);
  }

  try {
    const transporter = nodemailer.createTransport(buildTransportConfig(payload));
    await transporter.sendMail({
      from: payload.fromEmail,
      to: recipients.join(", "),
      subject: payload.title || "Wizarr Notification",
      text: payload.message || "",
      html: payload.htmlMessage || undefined,
    });

    writeResult(true, null);
  } catch (error) {
    writeResult(false, error.message || "SMTP send failed");
    process.exit(1);
  }
}

main();
