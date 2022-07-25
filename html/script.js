function enable_reaction_overlay(e) {
    document.getElementById("reaction-overlay").style.display = "block";
    var data = JSON.parse(decodeURI(e.target.parentElement.getAttribute("data")));
    document.getElementById("reaction-box").innerHTML = "";
    data.forEach((e) => {
        var p = document.createElement("p");
        p.innerHTML = e[0] + " " + e[1];
        document.getElementById("reaction-box").appendChild(p)
    });
}

function disable_reaction_overlay(e) {
    if (e.target !== e.currentTarget) return;
    document.getElementById("reaction-overlay").style.display = "none";
}

function live_search() {
    var messages = document.querySelectorAll(".message-box");
    var query = document.getElementById("search-input").value;
    var from = document.getElementById("search-date-from");
    var to = document.getElementById("search-date-to");

    function check_condition(message, query, to, from) {
        date = message.getAttribute("data");
        if (from.value.length > 0 && date <= from.valueAsNumber) { return false; }
        // Adjust by one day to make the selection inclusive from right.
        if (to.value.length > 0 && date >= to.valueAsNumber + 24*3600*1000) { return false; }
        return query.length == 0 || message.innerText.toLowerCase().includes(query.toLowerCase());
    }
    
    for (var i = 0; i < messages.length; i++) {
        if (check_condition(messages[i], query, to, from)) {
            messages[i].classList.remove("is-hidden");
        }
        else {
            messages[i].classList.add("is-hidden");
        }
    }
}

// This is from https://github.com/gilbitron/ui-avatar-svg under MIT licence.
class UIAvatarSvg {
    constructor() {
        this._text = 'AB';
        this._round = true;
        this._size = 64;
        this._bgColor = '#ff0000';
        this._textColor = '#ffffff';
        this._fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif";
        this._fontSize = 0.4;
        this._fontWeight = 'normal';
    }

    text(text) {
        this._text = text;
        return this;
    }

    round(round) {
        this._round = round;
        return this;
    }

    size(size) {
        this._size = size;
        return this;
    }

    bgColor(bgColor) {
        this._bgColor = bgColor;
        return this;
    }

    textColor(textColor) {
        this._textColor = textColor;
        return this;
    }

    fontFamily(fontFamily) {
        this._fontFamily = fontFamily;
        return this;
    }

    fontSize(fontSize) {
        this._fontSize = fontSize;
        return this;
    }

    fontWeight(fontWeight) {
        this._fontWeight = fontWeight;
        return this;
    }

    generate() {
        return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${this._size}px" height="${this._size}px" viewBox="0 0 ${this._size} ${this._size}" version="1.1"><${this._round ? 'circle' : 'rect'} fill="${this._bgColor}" width="${this._size}" height="${this._size}" cx="${this._size/2}" cy="${this._size/2}" r="${this._size/2}"/><text x="50%" y="50%" style="color: ${this._textColor};line-height: 1;font-family: ${this._fontFamily};" alignment-baseline="middle" text-anchor="middle" font-size="${Math.round(this._size*this._fontSize)}" font-weight="${this._fontWeight}" dy=".1em" dominant-baseline="middle" fill="${this._textColor}">${this._text}</text></svg>`
    }
}

// Show the search box.
document.getElementById("search-box").style.display = "block";
document.getElementById("messages").style.top = (document.getElementById("search-box").offsetHeight + 1) + 'px';
document.getElementById("group-avatar").style.top = document.getElementById("messages").style.top;

// Add delay for the search.
var timer;
document.getElementById("search-input").addEventListener("keyup", () => {
    clearTimeout(timer);
    timer = setTimeout(live_search, 300);
});

// Avatar letters.
var avatars = document.querySelectorAll(".avatar");
for (var i = 0; i < avatars.length; i++) {
    child = avatars[i].childNodes[0];
    if (child.tagName == "SPAN") {
        child.innerHTML = (new UIAvatarSvg())
          .text(child.getAttribute("data"))
          .size(64)
          .bgColor(child.getAttribute("color"))
          .textColor("#ffffff")
          .generate();
          }
}

// Disable overlays when ESC is pressed.
document.addEventListener("keyup", function(e) {
    if (e.key === "Escape") {
        document.getElementById("reaction-overlay").style.display = "none";
    }
});

