(assert
    (forall ((x1 Real))
    (exists ((y1 Real))
    (forall ((x2 Real))
    (exists ((y2 Real))
    (=> (and
            (and (or (not (< x1 0))  (= (+ y1 x1) 0))
                    (or (not (>= x1 0)) (= (- y1 x1) 0)))
            (and (or (not (< x2 0))  (= (- y2 x2) 0))
                    (or (not (>= x2 0)) (= (+ y2 x2) 0))))
        (not (= (+ y1 y2) 0))
    ))))))
