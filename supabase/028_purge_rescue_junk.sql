-- One more test row, minted after migration 027 by the phantom-guard bug
-- (27 Aug): the guard read a quoted OXS reference in a correct status reply
-- as a claim of opening, killed the reply, and the rescue net opened
-- 255-1130-26 with the conversation transcript as its description. The guard
-- is fixed (a reference alone is not a claim); this removes the row it left.

delete from requests where reference = '255-1130-26';
