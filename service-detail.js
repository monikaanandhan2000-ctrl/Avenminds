(function () {
  function qs(name) {
    var params = new URLSearchParams(window.location.search);
    return params.get(name);
  }

  function el(html) {
    var t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function renderList(ul, items) {
    ul.innerHTML = "";
    items.forEach(function (text) {
      var li = document.createElement("li");
      li.textContent = text;
      ul.appendChild(li);
    });
  }

  function renderRelated(grid, sector, currentSlug) {
    grid.innerHTML = "";
    var others = sector.services.filter(function (s) { return s.slug !== currentSlug; }).slice(0, 6);
    others.forEach(function (svc) {
      var card = el(
        '<a class="service-card" href="service-detail.html?sector=' + sector.id + '&service=' + svc.slug + '">' +
        '<h4>' + svc.name + '</h4>' +
        '<p>' + svc.cardBlurb + '</p>' +
        '<span class="sc-link">Learn more →</span>' +
        '</a>'
      );
      grid.appendChild(card);
    });
  }

  function renderSubnav(sectors, activeSector) {
    var nav = document.getElementById("subnav");
    var inner = document.getElementById("subnavInner");
    inner.innerHTML = "";
    sectors.forEach(function (s) {
      var a = document.createElement("a");
      a.href = s.id + ".html";
      a.textContent = s.name;
      if (s.id === activeSector.id) a.className = "current";
      inner.appendChild(a);
    });
    nav.style.display = "block";
  }

  function showNotFound() {
    document.getElementById("serviceTitle").textContent = "Service not found";
    document.getElementById("serviceLede").textContent =
      "We couldn't find that service. Browse all services from our services page, or get in touch and we'll point you in the right direction.";
    document.getElementById("serviceSectorTag").textContent = "Service";
  }

  fetch("js/services-data.json")
    .then(function (r) { return r.json(); })
    .then(function (sectors) {
      var sectorId = qs("sector");
      var serviceSlug = qs("service");
      var sector = sectors.find(function (s) { return s.id === sectorId; });
      var service = sector && sector.services.find(function (s) { return s.slug === serviceSlug; });

      if (!sector || !service) {
        showNotFound();
        return;
      }

      document.title = service.name + " | " + sector.name + " | AvenMinds";

      document.getElementById("breadcrumb").innerHTML =
        '<a href="index.html">Home</a> / <a href="services.html">Services</a> / ' +
        '<a href="' + sector.id + '.html">' + sector.name + '</a> / ' + service.name;

      document.getElementById("serviceSectorTag").textContent = sector.tag + " — " + sector.name;
      document.getElementById("serviceTitle").textContent = service.name;
      document.getElementById("serviceLede").textContent = service.detailBlurb;
      document.getElementById("serviceLede").removeAttribute("class");
      document.getElementById("serviceLede").className = "lede";

      renderList(document.getElementById("includesList"), service.includes);
      renderList(document.getElementById("benefitsList"), service.benefits);
      renderRelated(document.getElementById("relatedGrid"), sector, service.slug);
      renderSubnav(sectors, sector);

      document.getElementById("contactHeading").textContent = "Talk to us about " + service.name;
      var soi = document.getElementById("serviceOfInterest");
      if (soi) soi.value = service.name + " (" + sector.name + ")";
    })
    .catch(function () {
      showNotFound();
    });
})();
