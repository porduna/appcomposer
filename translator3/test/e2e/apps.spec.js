describe('apps page', function () {
    it('should do nothing much', function () {
        browser.get('http://localhost:5000/translator/web/index.html#/apps');

        // Check we have the expected category pills: Apps, Labs, Others
        var cats = element.all(by.css('.ac-category-pill'));
        expect(cats.count()).toEqual(3);

        //element(by.model('todoList.todoText')).sendKeys('write first protractor test');
        //element(by.css('[value="add"]')).click();

        //var todoList = element.all(by.repeater('todo in todoList.todos'));
        //expect(todoList.count()).toEqual(3);
        //expect(todoList.get(2).getText()).toEqual('write first protractor test');

        // You wrote your first test, cross it off the list
        //todoList.get(2).element(by.css('input')).click();
        //var completedAmount = element.all(by.css('.done-true'));
        //expect(completedAmount.count()).toEqual(2);
    });
});