//  Window scroll sticky class add
function windowScroll() {
  const navbar = document.getElementById("navbar");
  if (
      document.body.scrollTop >= 50 ||
      document.documentElement.scrollTop >= 50
  ) {
      navbar.classList.add("nav-sticky");
  } else {
      navbar.classList.remove("nav-sticky");
  }
}

window.addEventListener('scroll', (ev) => {
  ev.preventDefault();
  windowScroll();
})


//
/********************* scroll top js ************************/
//

var mybutton = document.getElementById("back-to-top");

// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function () {
  scrollFunction();
};

function scrollFunction() {
  if (
    document.body.scrollTop > 100 ||
    document.documentElement.scrollTop > 100
  ) {
    mybutton.style.display = "block";
  } else {
    mybutton.style.display = "none";
  }
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
  document.body.scrollTop = 0;
  document.documentElement.scrollTop = 0;
}


// 
// Typed Text animation (animation)
// 

try {
  var TxtType = function (el, toRotate, period) {
      this.toRotate = toRotate;
      this.el = el;
      this.loopNum = 0;
      this.period = parseInt(period, 10) || 2000;
      this.txt = '';
      this.tick();
      this.isDeleting = false;
  };
  TxtType.prototype.tick = function () {
      var i = this.loopNum % this.toRotate.length;
      var fullTxt = this.toRotate[i];
      if (this.isDeleting) {
          this.txt = fullTxt.substring(0, this.txt.length - 1);
      } else {
          this.txt = fullTxt.substring(0, this.txt.length + 1);
      }
      this.el.innerHTML = '<span class="wrap">' + this.txt + '</span>';
      var that = this;
      var delta = 200 - Math.random() * 100;
      if (this.isDeleting) { delta /= 2; }
      if (!this.isDeleting && this.txt === fullTxt) {
          delta = this.period;
          this.isDeleting = true;
      } else if (this.isDeleting && this.txt === '') {
          this.isDeleting = false;
          this.loopNum++;
          delta = 500;
      }
      setTimeout(function () {
          that.tick();
      }, delta);
  };
  function typewrite() {
      if (toRotate === 'undefined') {
          changeText()
      }
      else
          var elements = document.getElementsByClassName('typewrite');
      for (var i = 0; i < elements.length; i++) {
          var toRotate = elements[i].getAttribute('data-type');
          var period = elements[i].getAttribute('data-period');
          if (toRotate) {
              new TxtType(elements[i], JSON.parse(toRotate), period);
          }
      }
      // INJECT CSS
      var css = document.createElement("style");
      css.type = "text/css";
      css.innerHTML = ".typewrite > .wrap { border-right: 0.08em solid transparent}";
      document.body.appendChild(css);
  };
  window.onload(typewrite());
} catch(err) {
}


// particles

particlesJS("particles-js", {
  "particles": {
      "number": {
          "value": 80,
          "density": {
            "enable": false
          }
        },
    "color": {
      "value": "#1e304d"
    },
    "shape": {
      "type": ["circle","star","polygon"],
      "stroke": {
        "width": 0,
        "color": "#000000"
      }
    },
    "opacity": {
      "value": 0.5,
      "random": false,
      "anim": {
        "enable": false,
        "speed": 10,
        "opacity_min": 0.1,
        "sync": false
      }
    },
    "size": {

      "value": 3,  
      "random": true,
      "anim": {
        "enable": false,
        "speed": 40,
        "size_min": 0.1,
        "sync": false
      }
    },
    "line_linked": {
      "enable": false,
      "distance": 150,
      "color": "#ffffff",
      "opacity": 0.4,
      "width": 1
    },
    "move": {
      "enable": true,
      "speed": 3,
      "direction": "none",
      "random": true,
      "straight": false,
      "out_mode": "out",
      "bounce": true,
      "attract": {
        "enable": true,
        "rotateX": 600,
        "rotateY": 1200
      }
    }
  },
  "interactivity": {
    "detect_on": "canvas",
    "events": {
      "onhover": {
        "enable": true,
        "mode": "grab"
      },
      "onclick": {
        "enable": false,
        "mode": "push"
      },
      "resize": true
    },
    "modes": {
      "grab": {
        "distance": 150,
        "line_linked": {
          "opacity": 1
        }
      },
      "bubble": {
        "distance": 400,
        "size": 40,
        "duration": 2,
        "opacity": 8,
        "speed": 3
      },
      "repulse": {
        "distance": 200,
        "duration": 0.4
      },
      "push": {
        "particles_nb": 4
      },
      "remove": {
        "particles_nb": 2
      }
    }
  },
  "retina_detect": true
});




// Animaten js

 AOS.init();

document.addEventListener("DOMContentLoaded", function(){
    let svg = document.querySelector('.logos');
    svg.classList.add('active');
});

$(document).ready(function () {
  $("#searchResults").hide();
});
function searchByCode(xml_url, checked_svg) {
  var searchValue = document.getElementById("searchInput").value.trim();

  if (searchValue === '') {
      $("#searchResults").html('');
      $("#searchResults").slideUp(200);
      return;
  }

  $.ajax({
      url: xml_url,
      dataType: "xml",
      success: function (data) {
          var results = $(data).find("Code").filter(function () {
              return $(this).text().includes(searchValue);
          }).closest("Element");

          if (results.length > 0) {
              var output = "";
              results.each(function () {
                  var code = $(this).find("Code").text();
                  var name = $(this).find("Name").text();
                  var highlightedCode = code.replace(new RegExp(searchValue, "gi"), function (match) {
                      return '<span class="highlight">' + match + '</span>';
                  });
                  output += "<div class='result'><div class='result-code'>" + highlightedCode + "</div>" + " <div class='result-name'>" + name + `<img src="${checked_svg}"></div></div>`;
              });
              $("#searchResults").html(output);
              $("#searchResults").slideDown(200);
          } else {
              $("#searchResults").html("<div class='result'>Такого кода нет в нашей базе!</div>");
          }
      },
      error: function () {
          $("#searchResults").html("<div class='result'>Ошибка загрузки xml</div>");
      }
  });
}

function validateNumericInput(event) {
  var key = event.which || event.keyCode;
  if (key < 48 || key > 57) {
      $("#searchResults").html("<div class='result'>Введите код ВЭД, только цифры!</div>");
      $("#searchResults").slideDown(200);

      return false;
  }
  $("#searchResults").html('');
  return true;
}