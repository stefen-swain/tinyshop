function add(selectValue, selectText) {

    if (localStorage.getItem('cart') === null) {

        localStorage.setItem('cart', JSON.stringify([]));

    }

    let cart = JSON.parse(localStorage.getItem('cart'));

    cart.push(JSON.parse(selectValue));

    localStorage.setItem('cart', JSON.stringify(cart));

    alert(`You added ${selectText} to your cart.`);

}

async function main() {

    let uri = window.location.href;
    
    let classification = decodeURIComponent(uri.split('=')[1]);

    let offersResponse = await fetch('/server/offering/offers/'.concat(classification), {method: ['GET']});

    let offers = await offersResponse.json();

    let classificationDiv = document.getElementById('classificationOffers')

    for (let image of offers[0]['classification_images']) {

        let img = document.createElement('img');

        img.setAttribute('style', 'margin-top: 30px;');

        img.setAttribute('src', image);

        classificationDiv.appendChild(img);

    }

    let classificationH = document.createElement('h2');

    classificationH.innerText = offers[0]['classification'];

    classificationDiv.appendChild(classificationH);

    let classificationDescriptionDiv = document.createElement('div');

    classificationDescriptionDiv.innerHTML = offers[0]['classification_description'];

    classificationDiv.appendChild(classificationDescriptionDiv);

    let offersSelect = document.createElement('select');

    offersSelect.setAttribute('style', 'height: 50px;')

    for (let offer of offers) {

        let option = document.createElement('option');

        option.value = JSON.stringify(offer);

        option.textContent = offer.name + ' - $' + String(offer.price);

        offersSelect.appendChild(option);

    }

    classificationDiv.appendChild(offersSelect);

    let additionButton = document.createElement('button');

    additionButton.addEventListener('mouseup', () => {add(offersSelect.value, offersSelect.options[offersSelect.selectedIndex].text);});

    additionButton.innerText = 'Add to Cart';

    additionButton.className = 'dark-button';
    
    additionButton.setAttribute('style', 'font-size: 18px; height: 50px;');

    classificationDiv.appendChild(additionButton);

}

main();
