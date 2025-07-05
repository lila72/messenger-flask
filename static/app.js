let token = null;
let username = null;
let currentContact = null;
let socket = null;

function register() {
  fetch('/register', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      username: document.getElementById('login').value,
      password: document.getElementById('password').value
    })
  }).then(res => res.json()).then(alert);
}

function login() {
  fetch('/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      username: document.getElementById('login').value,
      password: document.getElementById('password').value
    })
  }).then(res => res.json()).then(data => {
    if (data.token) {
      token = data.token;
      username = document.getElementById('login').value;
      document.getElementById('auth').style.display = 'none';
      document.getElementById('chat').style.display = 'block';
      document.getElementById('user').innerText = username;
      initSocket();
      loadContacts();
    } else {
      alert(data.message);
    }
  });
}

function initSocket() {
  socket = io();
  socket.on('private_message', msg => {
    if (msg.sender === currentContact || msg.recipient === currentContact) {
      const div = document.createElement('div');
      div.innerText = `${msg.sender}: ${msg.content}`;
      document.getElementById('messages').appendChild(div);
    }
  });
}

function loadContacts() {
  fetch('/contacts', {
    headers: { 'Authorization': 'Bearer ' + token }
  }).then(res => res.json()).then(contacts => {
    const ul = document.getElementById('contacts');
    ul.innerHTML = '';
    contacts.forEach(c => {
      const li = document.createElement('li');
      li.innerText = c;
      li.onclick = () => openChat(c);
      ul.appendChild(li);
    });
  });
}

function openChat(contact) {
  currentContact = contact;
  socket.emit('join', { sender: username, recipient: contact });
  document.getElementById('messages').innerHTML = '';
}

function sendMessage() {
  const input = document.getElementById('messageInput');
  const msg = input.value;
  input.value = '';
  socket.emit('private_message', {
    sender: username,
    recipient: currentContact,
    content: msg
  });
}

function searchUsers() {
  const q = document.getElementById('search').value;
  if (!q) return;
  fetch('/users/' + q, {
    headers: { 'Authorization': 'Bearer ' + token }
  }).then(res => res.json()).then(users => {
    const results = document.getElementById('results');
    results.innerHTML = '';
    users.forEach(u => {
      const btn = document.createElement('button');
      btn.innerText = `Добавить ${u}`;
      btn.onclick = () => addContact(u);
      results.appendChild(btn);
    });
  });
}

function addContact(name) {
  fetch('/contacts', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username: name })
  }).then(res => res.json()).then(loadContacts);
}
