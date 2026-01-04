// web/static/js/scan.js

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('scan-form');
    const authenticatedCheckbox = document.getElementById('authenticated');
    const authFields = document.getElementById('auth-fields');

    authenticatedCheckbox.addEventListener('change', function() {
        authFields.style.display = this.checked ? 'block' : 'none';
    });

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = document.getElementById('submit-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Đang tạo scan...';

        const resetBtn = () => {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Bắt đầu quét';
        };

        const hostsText = document.getElementById('hosts').value.trim();
        const hosts = hostsText.split('\n').map(h => h.trim()).filter(Boolean);

        if (hosts.length === 0) {
            alert('Vui lòng nhập ít nhất 1 host');
            resetBtn();
            return;
        }

        const inputMode = document.getElementById('input-mode').value;
        const authenticated = authenticatedCheckbox.checked;

        const data = {
            hosts,
            input_mode: inputMode,
            authenticated
        };

        if (authenticated) {
            const os = document.getElementById('auth-os').value;
            const username = document.getElementById('auth-username').value.trim();
            const password = document.getElementById('auth-password').value;
            const keyfile = document.getElementById('auth-keyfile').value;
            const port = parseInt(document.getElementById('auth-port').value) || 22;

            if (!username) {
                alert('Username là bắt buộc');
                resetBtn();
                return;
            }

            if (!password && !keyfile) {
                alert('Cần password hoặc private key');
                resetBtn();
                return;
            }

            data.auth_data = {
                os,
                username,
                password: password || null,
                keyfile: keyfile || null,
                port
            };
        }

        try {
            const response = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Lỗi tạo scan');

            document.getElementById('scan-id').textContent = result.scan_id;
            document.getElementById('view-result-link').href = `/result/${result.scan_id}`;
            document.getElementById('scan-result').style.display = 'block';
            document.getElementById('scan-result').scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            alert('Lỗi: ' + err.message);
        } finally {
            resetBtn();
        }
    });
});
