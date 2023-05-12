async function main() {

    let classificationsResponse = await fetch('/server/offering/classifications', {method: 'GET'});

    let classifications = await classificationsResponse.json();

    const classificationsDiv = document.getElementById('classifications');

    for (const classification of classifications) {

        let img = document.createElement('img');

        img.setAttribute('src', classification.classification_cover_image);

        img.setAttribute('style', 'width: 65vw; max-width: 250px; margin-top: 30px;')

        classificationsDiv.appendChild(img);

        let anchor = document.createElement('a');

        anchor.setAttribute('href', '/classification?classification='.concat(encodeURIComponent(classification.classification)));

        anchor.setAttribute('style', 'margin-top: 10px;');

        anchor.innerText = classification.classification;

        classificationsDiv.appendChild(anchor);

    }

}

main();
